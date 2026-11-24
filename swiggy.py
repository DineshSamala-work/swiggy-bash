import argparse
import asyncio
import base64
import hashlib
import json
import os
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from tabulate import tabulate

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

DB_PATH = "swiggy_bash.db"
BUILDERS_CART_CAP_INR = 1000
SWIGGY_AUTH_BASE = "https://mcp.swiggy.com/auth"
SWIGGY_ENDPOINTS = {
    "food": "https://mcp.swiggy.com/food",
    "im": "https://mcp.swiggy.com/im",
    "dineout": "https://mcp.swiggy.com/dineout",
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS occasions (
                occasion_id TEXT PRIMARY KEY,
                user_id TEXT,
                occasion_type TEXT,
                fulfillment_mode TEXT,
                address_id TEXT,
                address_tag TEXT,
                total_pax INTEGER,
                veg_pax INTEGER,
                nv_pax INTEGER,
                state TEXT,
                order_id TEXT,
                hold_txn_id TEXT,
                hold_amount INTEGER,
                idempotency_key TEXT UNIQUE,
                payload JSON,
                scheduled_time TEXT,
                created_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS wallet_ledger (
                txn_id TEXT PRIMARY KEY,
                user_id TEXT,
                type TEXT,
                amount INTEGER,
                idempotency_key TEXT UNIQUE,
                timestamp TIMESTAMP
            )
        """)


init_db()

MOCK_USER = {
    "user_id": "usr_karthik_99",
    "name": "Karthik",
    "wallet_balance": 5000,
    "addresses": [
        {
            "id": "addr_work_01",
            "addressCategory": "Work",
            "tag": "office",
            "addressLine": "Cyber Towers, Hitec City, Hyderabad",
        },
        {
            "id": "addr_home_02",
            "addressCategory": "Home",
            "tag": "home",
            "addressLine": "Flat 402, Gachibowli, Hyderabad",
        },
    ],
    "resolution": {"defaultAddressId": "addr_work_01"},
}


async def agent_think(step_title: str, rationales: List[str]):
    print(f"\n{MAGENTA}{BOLD}[AGENT REASONING: {step_title.upper()}]{RESET}")
    for item in rationales:
        await asyncio.sleep(0.2)
        print(f" {DIM}-> {item}{RESET}")
    print()


def read_tool_data(result: Dict[str, Any]) -> Dict[str, Any]:
    if not result.get("success"):
        err_code = result.get("error_code", "TOOL_ERROR")
        err_msg = result.get("error", "Unknown MCP tool failure")
        raise RuntimeError(f"[{err_code}] {err_msg}")
    return result.get("structuredContent", {})


def generate_pkce_pair() -> Dict[str, str]:
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return {
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }


def build_swiggy_authorize_url(client_id: str, redirect_uri: str, code_challenge: str, scope: str = "mcp:tools") -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "scope": scope,
        "state": secrets.token_urlsafe(16),
    }
    return f"{SWIGGY_AUTH_BASE}/authorize?{urlencode(params)}"


async def run_live_mcp_probe(server: str = "food"):
    access_token = os.getenv("SWIGGY_MCP_ACCESS_TOKEN", "").strip()
    client_id = os.getenv("SWIGGY_MCP_CLIENT_ID", "").strip()
    redirect_uri = os.getenv("SWIGGY_MCP_REDIRECT_URI", "http://localhost:8765/callback")

    if not access_token:
        pkce = generate_pkce_pair()
        print(f"\n{CYAN}{BOLD}[LIVE SWIGGY MCP - OAUTH 2.1 + PKCE READY]{RESET}")
        print(f"- Endpoint:         {SWIGGY_ENDPOINTS.get(server, SWIGGY_ENDPOINTS['food'])}")
        print(f"- Challenge (S256): {pkce['code_challenge'][:18]}...")
        if client_id:
            print("- Authorize URL:\n ", build_swiggy_authorize_url(client_id, redirect_uri, pkce["code_challenge"]))
        else:
            print("- Tip: Set SWIGGY_MCP_ACCESS_TOKEN (or SWIGGY_MCP_CLIENT_ID) in env to run live Streamable HTTP tools/list.")
        return

    try:
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        url = SWIGGY_ENDPOINTS.get(server, SWIGGY_ENDPOINTS["food"])
        headers = {"Authorization": f"Bearer {access_token}"}
        async with streamablehttp_client(url=url, headers=headers) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_resp = await session.list_tools()
                names = [t.name for t in tools_resp.tools]
                print(f"{GREEN}[+] Connected to {url} — tools: {names}{RESET}")
    except Exception as exc:
        print(f"{YELLOW}[!] Live MCP probe note: {exc}{RESET}")


class SwiggyMCPClient:
    def __init__(self):
        self.seen_idempotency_keys = set()
        self.cart: Dict[str, Any] = {
            "addressId": None,
            "restaurantId": None,
            "restaurantName": None,
            "items": [],
            "couponCode": None,
            "discount": 0,
            "to_pay": 0,
        }
        self.placed_orders: Dict[str, Dict[str, Any]] = {}

        self.catalog = {
            "rest_meghana": {
                "id": "rest_meghana",
                "name": "Meghana Foods (Hitec City)",
                "availabilityStatus": "OPEN",
                "distanceKm": 1.6,
                "rating": 4.5,
                "diet_fit": "Dedicated Veg Paneer Handi + Chicken Dum Biryani",
                "simulate_stockout_on_dispatch": True,
                "menu": [
                    {"id": "item_nv_handi", "name": "Chicken Dum Biryani Handi (Serves 3-4)", "veg": False, "price": 460, "inStock": True},
                    {"id": "item_veg_handi", "name": "Paneer Tikka Biryani Handi (Dedicated Veg)", "veg": True, "price": 380, "inStock": True},
                    {"id": "item_im_treat", "name": "Instamart Celebration Sweet & Treat Pack", "veg": True, "price": 120, "inStock": True},
                ],
            },
            "rest_pista": {
                "id": "rest_pista",
                "name": "Pista House (Hitec City)",
                "availabilityStatus": "OPEN",
                "distanceKm": 1.9,
                "rating": 4.4,
                "diet_fit": "Verified Veg & Non-Veg Handis in Stock (Price-Matched)",
                "simulate_stockout_on_dispatch": False,
                "menu": [
                    {"id": "item_ph_nv", "name": "Pista House Zafrani Chicken Handi", "veg": False, "price": 460, "inStock": True},
                    {"id": "item_ph_veg", "name": "Pista House Veg Dum Biryani Handi", "veg": True, "price": 380, "inStock": True},
                    {"id": "item_ph_sweet", "name": "Instamart Dessert & Treat Add-On", "veg": True, "price": 120, "inStock": True},
                ],
            },
            "rest_closed": {
                "id": "rest_closed",
                "name": "Paradise Kitchen (Closed)",
                "availabilityStatus": "CLOSED",
                "distanceKm": 1.2,
                "rating": 4.2,
                "diet_fit": "Currently closed",
                "simulate_stockout_on_dispatch": False,
                "menu": [],
            },
        }

    def _recompute_cart(self):
        subtotal = sum(i["price"] * i["quantity"] for i in self.cart["items"])
        discount = self.cart["discount"] if subtotal >= 500 else 0
        self.cart["to_pay"] = max(0, subtotal - discount)

    async def call_tool(self, server: str, tool_name: str, args: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        await asyncio.sleep(0.25)

        if tool_name != "place_food_order" and idempotency_key:
            if idempotency_key in self.seen_idempotency_keys:
                return {"success": True, "structuredContent": {"idempotentReplay": True}}
            self.seen_idempotency_keys.add(idempotency_key)

        if tool_name == "get_addresses":
            return {
                "success": True,
                "structuredContent": {
                    "addresses": MOCK_USER["addresses"],
                    "resolution": MOCK_USER["resolution"],
                },
            }

        elif tool_name == "search_restaurants":
            open_restaurants = [
                r for r in self.catalog.values() if r["availabilityStatus"] == "OPEN"
            ]
            open_restaurants.sort(key=lambda r: (r["distanceKm"], -r["rating"]))
            return {"success": True, "structuredContent": {"restaurants": open_restaurants}}

        elif tool_name == "get_restaurant_menu":
            rest = self.catalog.get(args["restaurantId"])
            if not rest:
                return {"success": False, "error_code": "NOT_FOUND", "error": "Restaurant not found"}
            return {"success": True, "structuredContent": {"items": rest["menu"]}}

        elif tool_name == "update_food_cart":
            rest_id = args["restaurantId"]
            if self.cart["restaurantId"] and self.cart["restaurantId"] != rest_id:
                self.cart["items"] = []
                self.cart["couponCode"] = None
                self.cart["discount"] = 0

            self.cart["addressId"] = args["addressId"]
            self.cart["restaurantId"] = rest_id
            self.cart["restaurantName"] = args["restaurantName"]
            self.cart["items"] = args["cartItems"]
            self._recompute_cart()
            return {"success": True, "structuredContent": {"cart": dict(self.cart)}}

        elif tool_name == "fetch_food_coupons":
            return {
                "success": True,
                "structuredContent": {
                    "coupon_sections": [
                        {
                            "coupons": [
                                {"id": "BASH100", "applicable": True, "discount": 100, "desc": "Rs.100 off occasion cart"}
                            ]
                        }
                    ]
                },
            }

        elif tool_name == "apply_food_coupon":
            code = args["couponCode"]
            if code == "BASH100":
                self.cart["couponCode"] = code
                self.cart["discount"] = 100
                self._recompute_cart()
                return {"success": True, "structuredContent": {"applied": True, "to_pay": self.cart["to_pay"]}}
            return {"success": False, "error_code": "INVALID_COUPON", "error": "Coupon not applicable"}

        elif tool_name == "get_food_cart":
            self._recompute_cart()
            return {"success": True, "structuredContent": {"data": {"pricing": {"to_pay": self.cart["to_pay"]}}}}

        elif tool_name == "place_food_order":
            if args.get("simulate_5xx"):
                committed_id = f"ORD-SWG-{uuid.uuid4().hex[:6].upper()}"
                self.placed_orders[committed_id] = {
                    "orderId": committed_id,
                    "restaurantName": self.cart["restaurantName"],
                    "amount": self.cart["to_pay"],
                    "orderStatus": "PREPARING",
                    "etaText": "32 mins",
                }
                return {
                    "success": False,
                    "error_code": "HTTP_503",
                    "error": "Upstream gateway 503 after dispatch; verify with get_food_orders before retry.",
                }

            order_id = f"ORD-SWG-{uuid.uuid4().hex[:6].upper()}"
            record = {
                "orderId": order_id,
                "restaurantName": self.cart["restaurantName"],
                "amount": self.cart["to_pay"],
                "orderStatus": "CONFIRMED",
                "etaText": "30 mins",
            }
            self.placed_orders[order_id] = record
            return {"success": True, "structuredContent": record}

        elif tool_name == "get_food_orders":
            return {"success": True, "structuredContent": {"orders": list(self.placed_orders.values())}}

        elif tool_name == "track_food_order":
            rec = self.placed_orders.get(args["orderId"])
            if not rec:
                return {"success": False, "error_code": "ORDER_NOT_FOUND", "error": "Order not found"}
            return {"success": True, "structuredContent": {"orders": [rec]}}

        elif tool_name == "search_dineout_venues":
            veg_count = args.get("veg_count", 0)
            nv_count = args.get("nv_count", 0)
            venues = [
                {
                    "name": "Barbeque Nation (Hitec City)",
                    "dist_km": 1.4,
                    "rating": 4.5,
                    "cuisine": "Live Grill & Dual Buffet",
                    "deal": "Buffet @ Rs.799 + Birthday Dessert",
                    "diet_fit": f"Dedicated Veg grill + Non-Veg skewers ({nv_count} NV / {veg_count} Veg)",
                },
                {
                    "name": "The Bier Library",
                    "dist_km": 1.8,
                    "rating": 4.4,
                    "cuisine": "Microbrewery & Global Kitchen",
                    "deal": "20% off via Dineout Pay",
                    "diet_fit": "Full stonebaked veg mains & starters alongside non-veg platters",
                },
                {
                    "name": "AB's - Absolute Barbecues",
                    "dist_km": 2.2,
                    "rating": 4.6,
                    "cuisine": "Wish Grill & Multi-Cuisine",
                    "deal": "15% off total bill",
                    "diet_fit": "Separate vegetarian starters & main counters",
                },
            ]
            return {"success": True, "structuredContent": {"venues": venues}}

        elif tool_name == "reserve_table":
            return {
                "success": True,
                "structuredContent": {
                    "booking_id": f"DINE-{uuid.uuid4().hex[:6].upper()}",
                    "venue": args["venue_name"],
                    "pax": args["pax"],
                    "slot": args["slot"],
                    "status": "CONFIRMED",
                },
            }

        elif tool_name == "verify_dineout_reservation":
            if args.get("simulate_closure"):
                return {
                    "success": False,
                    "error_code": "VENUE_CLOSED",
                    "error": "Venue reported an unexpected closure on the day of the occasion.",
                }
            return {"success": True, "structuredContent": {"status": "CONFIRMED_ACTIVE"}}

        elif tool_name == "hold_wallet_balance":
            amount = args["amount"]
            if MOCK_USER["wallet_balance"] < amount:
                return {"success": False, "error_code": "INSUFFICIENT_FUNDS", "error": "Insufficient wallet balance"}
            MOCK_USER["wallet_balance"] -= amount
            txn_id = f"HOLD-{uuid.uuid4().hex[:8]}"
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO wallet_ledger (txn_id, user_id, type, amount, idempotency_key, timestamp) VALUES (?, ?, 'HOLD', ?, ?, ?)",
                    (txn_id, MOCK_USER["user_id"], amount, idempotency_key, datetime.now()),
                )
            return {
                "success": True,
                "structuredContent": {
                    "hold_txn_id": txn_id,
                    "amount": amount,
                    "remaining_free_balance": MOCK_USER["wallet_balance"],
                },
            }

        elif tool_name == "capture_wallet_hold":
            capture_txn = f"CAP-{uuid.uuid4().hex[:8]}"
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO wallet_ledger (txn_id, user_id, type, amount, idempotency_key, timestamp) VALUES (?, ?, 'CAPTURE', ?, ?, ?)",
                    (capture_txn, MOCK_USER["user_id"], args["amount"], idempotency_key, datetime.now()),
                )
            return {"success": True, "structuredContent": {"capture_txn_id": capture_txn, "status": "FUNDS_SETTLED"}}

        elif tool_name == "release_wallet_hold":
            amount = args["amount"]
            MOCK_USER["wallet_balance"] += amount
            rel_txn = f"REL-{uuid.uuid4().hex[:8]}"
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO wallet_ledger (txn_id, user_id, type, amount, idempotency_key, timestamp) VALUES (?, ?, 'RELEASE', ?, ?, ?)",
                    (rel_txn, MOCK_USER["user_id"], amount, idempotency_key, datetime.now()),
                )
            return {
                "success": True,
                "structuredContent": {"refund_txn_id": rel_txn, "restored_balance": MOCK_USER["wallet_balance"]},
            }

        return {"success": False, "error_code": "UNKNOWN_TOOL", "error": f"Unknown tool: {tool_name}"}


def _update_occasion_state(occasion_id: str, state: str, order_id: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        if order_id:
            conn.execute(
                "UPDATE occasions SET state = ?, order_id = ? WHERE occasion_id = ?",
                (state, order_id, occasion_id),
            )
        else:
            conn.execute(
                "UPDATE occasions SET state = ? WHERE occasion_id = ?",
                (state, occasion_id),
            )


async def main(live_probe: bool = False, server: str = "food"):
    if live_probe:
        await run_live_mcp_probe(server=server)
        return

    mcp = SwiggyMCPClient()
    occasion_id = f"occ_{uuid.uuid4().hex[:8]}"

    print("\n" + "=" * 70)
    print(f"{MAGENTA}{BOLD}[FCM PUSH NOTIFICATION SIMULATED]{RESET}")
    print(f"{BOLD}Title:{RESET} Birthday week loaded, {MOCK_USER['name']}! (e.g., Apr 10 -> Apr 13)")
    print(f"{BOLD}Body:{RESET}  Team treat or family celebration on the horizon? Let's get the spread locked.")
    print("=" * 70)

    print(f"\n{CYAN}{BOLD}Who are we planning this for?{RESET}")
    print(f" {BOLD}[1]{RESET} Office Colleagues Treat")
    print(f" {BOLD}[2]{RESET} Family Celebration")

    mode = input(f"\n{YELLOW}Choose option (1/2, default: 1): {RESET}").strip() or "1"
    is_office = mode == "1"
    desired_category = "Work" if is_office else "Home"

    addr_data = read_tool_data(
        await mcp.call_tool("food", "get_addresses", {}, idempotency_key=f"idem_addr_{occasion_id}")
    )
    addresses = addr_data["addresses"]
    default_id = addr_data["resolution"]["defaultAddressId"]
    selected_addr = (
        next((a for a in addresses if a["addressCategory"] == desired_category), None)
        or next((a for a in addresses if a["id"] == default_id), None)
        or addresses[0]
    )
    addr_tag = selected_addr["tag"]
    print(f"{GREEN}[+] Resolved Address ({selected_addr['addressCategory']}):{RESET} {selected_addr['addressLine']}")

    prompt_pax = "How many colleagues on the floor? " if is_office else "How many family members joining? "
    while True:
        pax_in = input(f"\n{YELLOW}{prompt_pax}(default: 8): {RESET}").strip() or "8"
        if pax_in.isdigit() and int(pax_in) > 0:
            total_pax = int(pax_in)
            break
        print("Please enter a valid positive number.")

    print(f"\n{CYAN}{BOLD}Dietary Parity Check:{RESET}")
    print(f"{DIM}Ensuring vegetarian guests receive full dedicated primary platters, not afterthought sides.{RESET}")
    while True:
        veg_in = input(f"{YELLOW}How many pure VEG members in this group? (0-{total_pax}, default: 2): {RESET}").strip() or "2"
        if veg_in.isdigit() and 0 <= int(veg_in) <= total_pax:
            veg_pax = int(veg_in)
            nv_pax = total_pax - veg_pax
            break
        print(f"Please enter a valid count between 0 and {total_pax}.")

    print(f"{GREEN}[+] Locked Ratios: {BOLD}{nv_pax} Non-Veg{RESET} and {BOLD}{veg_pax} Dedicated Veg{RESET} guests.")

    print(f"\n{CYAN}{BOLD}How do you want to do this?{RESET}")
    print(f" {BOLD}[1]{RESET} Planning to Step Out & Reserve Table (Dineout)")
    print(f" {BOLD}[2]{RESET} Order Food Delivery to {addr_tag.title()} (Swiggy Food + Instamart)")

    fulfillment = input(f"\n{YELLOW}Choose option (1/2, default: 2): {RESET}").strip() or "2"

    if fulfillment == "1":
        slot = input(f"\n{YELLOW}Preferred day & time slot? (default: Apr 13, 1:30 PM): {RESET}").strip() or "Apr 13, 1:30 PM"
        await agent_think("Dineout Venue Search", [
            f"Searching OPEN group venues near {selected_addr['addressLine']}...",
            f"Prioritizing dedicated Veg + Non-Veg options for {nv_pax} NV / {veg_pax} Veg guests.",
        ])
        venue_data = read_tool_data(
            await mcp.call_tool(
                "dineout",
                "search_dineout_venues",
                {"addressId": selected_addr["id"], "veg_count": veg_pax, "nv_count": nv_pax},
                idempotency_key=f"idem_search_dine_{occasion_id}",
            )
        )
        venues = venue_data["venues"]
        rows = [
            [f"[{i}]", v["name"], f"{v['rating']}*", f"{v['dist_km']} km", v["diet_fit"], v["deal"]]
            for i, v in enumerate(venues, 1)
        ]
        print("\n" + tabulate(rows, headers=["#", "Restaurant", "Rating", "Dist", "Dietary Fit", "Offer"], tablefmt="fancy_grid"))

        while True:
            pick = input(f"\n{YELLOW}Which restaurant would you like to reserve? (1-{len(venues)}): {RESET}").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(venues):
                chosen_venue = venues[int(pick) - 1]
                break
            print(f"Please enter a number between 1 and {len(venues)}.")

        booking = read_tool_data(
            await mcp.call_tool(
                "dineout",
                "reserve_table",
                {"venue_name": chosen_venue["name"], "pax": total_pax, "slot": slot},
                idempotency_key=f"idem_res_dine_{occasion_id}",
            )
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO occasions (
                    occasion_id, user_id, occasion_type, fulfillment_mode,
                    address_id, address_tag, total_pax, veg_pax, nv_pax, state,
                    order_id, hold_txn_id, hold_amount, idempotency_key, payload,
                    scheduled_time, created_at
                )
                VALUES (?, ?, ?, 'dineout', ?, ?, ?, ?, ?, 'CONFIRMED', NULL, NULL, 0, ?, ?, ?, ?)
            """, (
                occasion_id, MOCK_USER["user_id"], addr_tag, selected_addr["id"], addr_tag,
                total_pax, veg_pax, nv_pax, f"idem_occ_{occasion_id}", "{}", slot, datetime.now(),
            ))

        print("\n" + "=" * 70)
        print(f"{GREEN}{BOLD}[DINEOUT TABLE CONFIRMED]{RESET}")
        print(f"- Booking ID: {CYAN}{booking['booking_id']}{RESET}")
        print(f"- Venue:      {BOLD}{booking['venue']}{RESET}")
        print(f"- Guests:     {booking['pax']} ({nv_pax} Non-Veg / {veg_pax} Veg)")
        print(f"- Slot:       {booking['slot']}")
        print("=" * 70)

        print(f"\n{YELLOW}[DURABLE STATE PERSISTED]{RESET} Occasion '{CYAN}{occasion_id}{RESET}' saved as CONFIRMED.")
        print(f"{DIM}Simulating Day-T morning check prior to {slot}...{RESET}")
        await asyncio.sleep(0.8)

        await agent_think("Day-T Dineout Venue Health Audit", [
            f"Verifying reservation {booking['booking_id']} at {chosen_venue['name']}...",
            f"Simulating unexpected closure on event day for {chosen_venue['name']}.",
            "Fetching open nearby alternatives matching dietary ratios...",
        ])

        audit_res = await mcp.call_tool(
            "dineout",
            "verify_dineout_reservation",
            {"booking_id": booking["booking_id"], "simulate_closure": True},
            idempotency_key=f"idem_audit_dine_{occasion_id}",
        )

        if not audit_res.get("success") and audit_res.get("error_code") == "VENUE_CLOSED":
            _update_occasion_state(occasion_id, "ALERT_VENUE_CLOSED")
            print(f"{RED}{BOLD}[DAY-T ALERT: VENUE CLOSED]{RESET} {chosen_venue['name']} is closed today ({audit_res['error']}).")
            print(f"{CYAN}Let's pick a backup venue for {total_pax} guests ({nv_pax} NV / {veg_pax} Veg):{RESET}\n")

            alt_venues = [v for v in venues if v["name"] != chosen_venue["name"]]
            alt_rows = [
                [f"[{i}]", v["name"], f"{v['rating']}*", f"{v['dist_km']} km", v["diet_fit"], v["deal"]]
                for i, v in enumerate(alt_venues, 1)
            ]
            print(tabulate(alt_rows, headers=["#", "Replacement Venue", "Rating", "Dist", "Dietary Fit", "Offer"], tablefmt="fancy_grid"))

            rescue_pick = input(f"\n{YELLOW}Choose replacement (1-{len(alt_venues)}) or [C] to cancel: {RESET}").strip()
            if rescue_pick.isdigit() and 1 <= int(rescue_pick) <= len(alt_venues):
                new_venue = alt_venues[int(rescue_pick) - 1]
                new_booking = read_tool_data(
                    await mcp.call_tool(
                        "dineout",
                        "reserve_table",
                        {"venue_name": new_venue["name"], "pax": total_pax, "slot": slot},
                        idempotency_key=f"idem_rescue_dine_{occasion_id}",
                    )
                )
                _update_occasion_state(occasion_id, "REBOOKED_CONFIRMED")
                print(f"\n{GREEN}{BOLD}[REPLACEMENT TABLE CONFIRMED]{RESET}")
                print(f"- Closed Venue:   {RED}{chosen_venue['name']}{RESET}")
                print(f"- New Venue:      {BOLD}{new_booking['venue']}{RESET}")
                print(f"- New Booking ID: {CYAN}{new_booking['booking_id']}{RESET}")
                print(f"- Guests & Slot:  {total_pax} ({nv_pax} NV / {veg_pax} Veg) @ {slot}")
            else:
                _update_occasion_state(occasion_id, "CANCELED_VENUE_CLOSED")
                print(f"\n{YELLOW}[+] Reservation canceled and marked CANCELED_VENUE_CLOSED in SQLite.{RESET}")

        print("\n" + "=" * 70)
        print(f"{CYAN}Last-minute change of plans?{RESET} No worry, I will be here.\n")
        return

    treat_time = input(f"\n{YELLOW}What time is lunch/dinner scheduled? (default: 1:15 PM): {RESET}").strip() or "1:15 PM"

    rest_data = read_tool_data(
        await mcp.call_tool(
            "food",
            "search_restaurants",
            {"addressId": selected_addr["id"], "query": "biryani"},
            idempotency_key=f"idem_search_rest_{occasion_id}",
        )
    )
    primary_rest = next((r for r in rest_data["restaurants"] if r["availabilityStatus"] == "OPEN"), None)
    if not primary_rest:
        raise RuntimeError("No OPEN restaurants found.")

    menu_data = read_tool_data(
        await mcp.call_tool(
            "food",
            "get_restaurant_menu",
            {"addressId": selected_addr["id"], "restaurantId": primary_rest["id"]},
            idempotency_key=f"idem_menu_{primary_rest['id']}_{occasion_id}",
        )
    )
    in_stock_items = [item for item in menu_data["items"] if item["inStock"]]

    nv_qty = 1 if nv_pax > 0 else 0
    veg_qty = 1 if veg_pax > 0 else 0
    cart_items = []
    for item in in_stock_items:
        if not item["veg"] and nv_qty > 0:
            cart_items.append({"menu_item_id": item["id"], "name": item["name"], "price": item["price"], "quantity": nv_qty})
        elif item["veg"] and "Handi" in item["name"] and veg_qty > 0:
            cart_items.append({"menu_item_id": item["id"], "name": item["name"], "price": item["price"], "quantity": veg_qty})

    im_item = next((i for i in in_stock_items if "Instamart" in i["name"]), None)
    projected_raw = sum(x["price"] * x["quantity"] for x in cart_items)
    if im_item and (projected_raw + im_item["price"] - 100) <= BUILDERS_CART_CAP_INR:
        im_label = "Celebration Treats (Instamart)" if is_office else "Traditional Sweets & Desserts (Instamart)"
        cart_items.append({"menu_item_id": im_item["id"], "name": im_label, "price": im_item["price"], "quantity": 1})

    cart_data = read_tool_data(
        await mcp.call_tool(
            "food",
            "update_food_cart",
            {
                "addressId": selected_addr["id"],
                "restaurantId": primary_rest["id"],
                "restaurantName": primary_rest["name"],
                "cartItems": cart_items,
            },
            idempotency_key=f"idem_cart_{occasion_id}",
        )
    )

    coupon_data = read_tool_data(
        await mcp.call_tool(
            "food",
            "fetch_food_coupons",
            {"restaurantId": primary_rest["id"], "addressId": selected_addr["id"]},
            idempotency_key=f"idem_coupons_{occasion_id}",
        )
    )
    applicable_coupon = next(
        (c for s in coupon_data["coupon_sections"] for c in s["coupons"] if c["applicable"]), None
    )
    if applicable_coupon:
        await mcp.call_tool(
            "food",
            "apply_food_coupon",
            {"couponCode": applicable_coupon["id"], "addressId": selected_addr["id"]},
            idempotency_key=f"idem_apply_cpn_{occasion_id}",
        )

    cart_check = read_tool_data(
        await mcp.call_tool(
            "food",
            "get_food_cart",
            {"addressId": selected_addr["id"], "restaurantName": primary_rest["name"]},
            idempotency_key=f"idem_get_cart_{occasion_id}",
        )
    )
    final_amount = cart_check["data"]["pricing"]["to_pay"]
    if final_amount > BUILDERS_CART_CAP_INR:
        raise RuntimeError(f"Cart total Rs.{final_amount} exceeds Builders Club Rs.{BUILDERS_CART_CAP_INR} cap.")

    print("\n" + "=" * 70)
    print(f"{BOLD}DIETARY-BALANCED SPREAD ({total_pax} PAX | {nv_pax} NV / {veg_pax} Veg):{RESET}")
    for ci in cart_data["cart"]["items"]:
        print(f" - {ci['name']} (x{ci['quantity']}) - Rs.{ci['price'] * ci['quantity']}")
    print(f" {BOLD}Total to Pre-Authorize (Cap <= Rs.{BUILDERS_CART_CAP_INR}): Rs.{final_amount}{RESET}")
    print("=" * 70)

    confirm = input(f"\n{YELLOW}Approve pre-authorization hold of Rs.{final_amount}? (Y/N, default Y): {RESET}").strip().lower() or "y"
    if confirm != "y":
        print("Flow canceled.")
        return

    hold_res = read_tool_data(
        await mcp.call_tool(
            "wallet",
            "hold_wallet_balance",
            {"amount": final_amount},
            idempotency_key=f"idem_hold_{occasion_id}",
        )
    )
    print(f"{GREEN}[+] Escrow Hold Placed:{RESET} {CYAN}{hold_res['hold_txn_id']}{RESET} (Rs.{final_amount})")

    payload_snapshot = json.dumps({"cart_items": cart_items, "coupon": applicable_coupon["id"] if applicable_coupon else None})
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO occasions (
                occasion_id, user_id, occasion_type, fulfillment_mode,
                address_id, address_tag, total_pax, veg_pax, nv_pax, state,
                order_id, hold_txn_id, hold_amount, idempotency_key, payload,
                scheduled_time, created_at
            )
            VALUES (?, ?, ?, 'food_delivery', ?, ?, ?, ?, ?, 'QUEUED', NULL, ?, ?, ?, ?, ?, ?)
        """, (
            occasion_id, MOCK_USER["user_id"], addr_tag, selected_addr["id"], addr_tag,
            total_pax, veg_pax, nv_pax, hold_res["hold_txn_id"], final_amount,
            f"idem_occ_{occasion_id}", payload_snapshot, treat_time, datetime.now(),
        ))

    print(f"\n{BOLD}[DAY T: DISPATCH WORKER PRE-FLIGHT CHECK]{RESET}")
    await asyncio.sleep(0.8)

    print(f"{RED}{BOLD}RECONCILIATION ALERT:{RESET} {primary_rest['name']} ran out of Handis before dispatch.")
    fallback_choice = input(f"{YELLOW}Action: [1] Swap to Pista House (Price-Matched) | [2] Release Escrow Hold: {RESET}").strip() or "1"

    if fallback_choice == "1":
        backup_rest = mcp.catalog["rest_pista"]
        backup_items = [
            {"menu_item_id": i["id"], "name": i["name"], "price": i["price"], "quantity": 1}
            for i in backup_rest["menu"]
        ]
        read_tool_data(
            await mcp.call_tool(
                "food",
                "update_food_cart",
                {
                    "addressId": selected_addr["id"],
                    "restaurantId": backup_rest["id"],
                    "restaurantName": backup_rest["name"],
                    "cartItems": backup_items,
                },
                idempotency_key=f"idem_swap_cart_{occasion_id}",
            )
        )

        place_res = await mcp.call_tool(
            "food",
            "place_food_order",
            {"addressId": selected_addr["id"], "paymentMethod": "WalletEscrow", "simulate_5xx": True},
        )
        if place_res.get("success"):
            order_id = place_res["structuredContent"]["orderId"]
        else:
            print(f"{YELLOW}[!] place_food_order returned {place_res.get('error_code')} (not idempotent) -> checking get_food_orders...{RESET}")
            orders_data = read_tool_data(await mcp.call_tool("food", "get_food_orders", {}))
            existing = next((o for o in orders_data["orders"] if o["restaurantName"] == backup_rest["name"]), None)
            if existing:
                order_id = existing["orderId"]
                print(f"{GREEN}[+] Recovered already-committed order {CYAN}{order_id}{RESET} without duplicate placement!{RESET}")
            else:
                placed_retry = read_tool_data(
                    await mcp.call_tool("food", "place_food_order", {"addressId": selected_addr["id"], "paymentMethod": "WalletEscrow"})
                )
                order_id = placed_retry["orderId"]

        capture_res = read_tool_data(
            await mcp.call_tool(
                "wallet",
                "capture_wallet_hold",
                {"hold_txn_id": hold_res["hold_txn_id"], "amount": final_amount},
                idempotency_key=f"idem_cap_{occasion_id}",
            )
        )
        _update_occasion_state(occasion_id, "DISPATCHED_SETTLED", order_id=order_id)

        track_data = read_tool_data(await mcp.call_tool("food", "track_food_order", {"orderId": order_id}))
        tracked = track_data["orders"][0]
        print(f"\n{GREEN}{BOLD}[ORDER PLACED, ESCROW CAPTURED & TRACKING ACTIVE]{RESET}")
        print(f"- Order ID:         {CYAN}{tracked['orderId']}{RESET}")
        print(f"- Kitchen:          {BOLD}{tracked['restaurantName']}{RESET}")
        print(f"- Status / ETA:     {tracked['orderStatus']} ({tracked['etaText']})")
        print(f"- Escrow Capture:   {capture_res['capture_txn_id']} (Rs.{final_amount})")
    else:
        rel_res = read_tool_data(
            await mcp.call_tool(
                "wallet",
                "release_wallet_hold",
                {"hold_txn_id": hold_res["hold_txn_id"], "amount": final_amount},
                idempotency_key=f"idem_rel_{occasion_id}",
            )
        )
        _update_occasion_state(occasion_id, "CANCELED_RELEASED")
        print(f"\n{YELLOW}[+] Escrow released in full! Wallet Balance: Rs.{rel_res['restored_balance']}{RESET}")

    print("\n" + "=" * 70)
    print(f"{CYAN}Last-minute change of plans?{RESET} No worry, I will be here.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Swiggy Bash Occasion Copilot")
    parser.add_argument("--live-probe", action="store_true", help="Run OAuth 2.1 PKCE + Streamable HTTP tools/list probe")
    parser.add_argument("--server", default="food", choices=["food", "im", "dineout"], help="Target MCP server for live probe")
    args = parser.parse_args()
    asyncio.run(main(live_probe=args.live_probe, server=args.server))
