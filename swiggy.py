import asyncio
from typing import Dict, Any, List
from tabulate import tabulate

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

MOCK_USER_PROFILE = {
    "name": "Karthik",
    "dob": "1998-11-24",
    "wallet_balance": 5500,
    "addresses": [
        {
            "id": "addr_off_01",
            "tag": "office",
            "name": "Cyber Towers, Hitec City, Hyderabad",
            "lat": 17.4504,
            "lng": 78.3808,
        },
        {
            "id": "addr_hm_02",
            "tag": "home",
            "name": "Flat 402, Gachibowli, Hyderabad",
            "lat": 17.4401,
            "lng": 78.3489,
        },
    ],
}


async def agent_think(step_title: str, rationales: List[str]):
    print(f"\n{MAGENTA}{BOLD}[AGENT REASONING: {step_title.upper()}]{RESET}")
    for item in rationales:
        await asyncio.sleep(0.25)
        print(f" {DIM}-> {item}{RESET}")
    print()


class SwiggyMCPClient:
    def __init__(self, token: str = "demo_token"):
        self.token = token

    async def call_tool(self, server: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.3)
        veg_count = args.get("veg_count", 0)
        nv_count = args.get("nv_count", 0)

        if tool_name == "search_dineout_venues":
            venues = [
                {
                    "name": "Barbeque Nation (Hitec City)",
                    "dist_km": 1.4,
                    "rating": 4.5,
                    "cuisine": "Live Grill & Dual Buffet",
                    "deal": "Buffet @ Rs.799 + Free Birthday Cake",
                    "veg_friendly_tag": f"[OK] Dedicated Veg grill station on table ({veg_count} veg guests catered seamlessly)",
                },
                {
                    "name": "The Bier Library / Ironhill",
                    "dist_km": 1.8,
                    "rating": 4.4,
                    "cuisine": "Microbrewery & Global Kitchen",
                    "deal": "20% off via Dineout Pay",
                    "veg_friendly_tag": "[OK] Rich gourmet veg menu: Stonebaked pizzas & paneer bites alongside craft meats",
                },
                {
                    "name": "AB's - Absolute Barbecues",
                    "dist_km": 2.2,
                    "rating": 4.6,
                    "cuisine": "Custom Wish Grill & Dual Counters",
                    "deal": "15% off total bill",
                    "veg_friendly_tag": "[OK] Separate vegetarian barbecue skewers & exotic veg counters",
                },
            ]
            return {"success": True, "venues": venues}

        elif tool_name == "reserve_table":
            return {
                "success": True,
                "booking_id": "DINEOUT-RES-91823",
                "venue": args.get("venue_name"),
                "pax": args.get("pax"),
                "veg_split": f"{veg_count} Veg / {nv_count} Non-Veg",
                "slot": args.get("slot"),
                "status": "CONFIRMED_IMMEDIATE",
            }

        elif tool_name == "search_dual_food_combos":
            combos = [
                {
                    "id": "c1",
                    "title": "Dual Hyderabadi Handi Feast (No One Left Behind)",
                    "restaurant": "Meghana Foods / Pista House",
                    "rating": 4.5,
                    "tag": f"[*] Calibrated for {nv_count} Non-Veg & {veg_count} Pure Veg guests",
                    "nv_items": [
                        {"name": "Chicken Dum Biryani Handi (Serves 4-5)", "qty": max(1, round(nv_count / 4)), "price": 750 * max(1, round(nv_count / 4))},
                        {"name": "Chicken 65 Large Starter Platter", "qty": 1, "price": 420},
                    ],
                    "veg_items": [
                        {"name": "Paneer Tikka Biryani Family Handi (Dedicated Veg Prep)", "qty": max(1, round(veg_count / 3)), "price": 550 * max(1, round(veg_count / 3))},
                        {"name": "Crispy Corn & Veg Manchurian Starter Tray", "qty": 1, "price": 340},
                    ],
                    "drinks": {"name": "Cold Drinks / Cans Assorted Pack", "qty": veg_count + nv_count, "price": 30 * (veg_count + nv_count)},
                    "coupon": "OFFICEBASH",
                    "discount": 350,
                },
                {
                    "id": "c2",
                    "title": "Artisanal Pizza & Starters Feast",
                    "restaurant": "Tossin / Brik Oven",
                    "rating": 4.4,
                    "tag": f"[+] Equal-Split Gourmet Crusts for {nv_count} NV + {veg_count} Veg",
                    "nv_items": [
                        {"name": "Large Peri Peri & BBQ Chicken Pizzas", "qty": max(1, round(nv_count / 3)), "price": 620 * max(1, round(nv_count / 3))},
                        {"name": "Smoked Chicken Wings Bucket", "qty": 1, "price": 450},
                    ],
                    "veg_items": [
                        {"name": "Large Gourmet Farmhouse & Paneer Supreme Pizzas", "qty": max(1, round(veg_count / 3)), "price": 540 * max(1, round(veg_count / 3))},
                        {"name": "Cheesy Garlic Breadsticks & Dips", "qty": 2, "price": 360},
                    ],
                    "drinks": {"name": "Soft Beverage Pack", "qty": veg_count + nv_count, "price": 25 * (veg_count + nv_count)},
                    "coupon": "TEAMPIZZA",
                    "discount": 300,
                },
            ]
            return {"success": True, "combos": combos}

        elif tool_name == "search_instamart_treats":
            treats = [
                {"id": "im_1", "name": "Cadbury Celebrations Rich Dry Fruit Box (Pack of 2)", "price": 450},
                {"id": "im_2", "name": "Ferrero Rocher Sharing Box (16 Pcs)", "price": 599},
                {"id": "im_3", "name": "Assorted Soft Drink & Juice Can Cooler (Chilled)", "price": 320},
            ]
            return {"success": True, "treats": treats}

        elif tool_name == "debit_swiggy_wallet":
            amount = args.get("amount")
            bal = MOCK_USER_PROFILE["wallet_balance"]
            new_bal = bal - amount
            MOCK_USER_PROFILE["wallet_balance"] = new_bal
            return {
                "success": True,
                "amount_debited": amount,
                "remaining_balance": new_bal,
                "txn_id": "TXN-SWG-9021884",
                "payment_mode": "Swiggy Money Wallet",
            }

        elif tool_name == "fire_delayed_order":
            return {
                "success": True,
                "order_id": "SWIGGY-ORD-90219",
                "delivery_eta": args.get("scheduled_time", "1:15 PM"),
                "status": "DISPATCHED_TO_KITCHEN",
            }

        return {"success": False, "error": "Unknown tool"}

async def main():
    mcp = SwiggyMCPClient()

    print("\n" + "=" * 68)
    print(f"{MAGENTA}{BOLD}[FCM PUSH NOTIFICATION SIMULATED]{RESET}")
    print(f"{BOLD}Title:{RESET} Birthday week loaded, {MOCK_USER_PROFILE['name']}! ")
    print(f"{BOLD}Body:{RESET}  Turning 26 this week? Team treat pending ah, or family dinner?")
    print("=" * 68)

    print(f"\n{CYAN}{BOLD}Who are we celebrating with?{RESET}")
    print(f" {BOLD}[1]{RESET} Office Colleagues Treat")
    print(f" {BOLD}[2]{RESET} Family / Close Circle Celebration")

    mode = input(f"\n{YELLOW}Choose an option (1/2, default: 1): {RESET}").strip() or "1"
    is_office = (mode == "1")
    addr_obj = MOCK_USER_PROFILE["addresses"][0] if is_office else MOCK_USER_PROFILE["addresses"][1]

    print(f"\n{BOLD}Target Location Tagged:{RESET} {CYAN}{addr_obj['name']}{RESET}")

    if is_office:
        while True:
            total_in = input(f"\n{YELLOW}How many total people in the office gang? (e.g., 8, 12): {RESET}").strip() or "8"
            if total_in.isdigit() and int(total_in) > 0:
                total_pax = int(total_in)
                break
            print("Please enter a valid number of colleagues.")

        print(f"\n{CYAN}{BOLD}Crucial check so everyone gets treated right:{RESET}")
        print(f"{DIM}Someone in the squad might be strict veg--we want to make sure they get a full, high-quality spread too!{RESET}")

        while True:
            veg_in = input(f"{YELLOW}How many pure VEG members in the group? (0-{total_pax}, default: 2): {RESET}").strip() or "2"
            if veg_in.isdigit() and 0 <= int(veg_in) <= total_pax:
                veg_pax = int(veg_in)
                nv_pax = total_pax - veg_pax
                break
            print(f"Please enter a number between 0 and {total_pax}.")

        print(f"\n{GREEN}[+] Locked Gang Split: {BOLD}{nv_pax} Non-Veg{RESET} and {BOLD}{veg_pax} Pure Veg{RESET} colleague(s).")
    else:
        total_pax = int(input(f"\n{YELLOW}How many family members joining? (default: 5): {RESET}").strip() or "5")
        veg_pax = max(1, round(total_pax * 0.4))
        nv_pax = total_pax - veg_pax

    print(f"\n{CYAN}{BOLD}How are you planning to celebrate?{RESET}")
    print(f" {BOLD}[1]{RESET} Step out for lunch / Reserve table near office {DIM}(Dineout){RESET}")
    print(f" {BOLD}[2]{RESET} Order food & celebration treats to office reception {DIM}(Swiggy Food & Instamart){RESET}")

    branch = input(f"\n{YELLOW}Choose an option (1/2, default: 2): {RESET}").strip() or "2"

    if branch == "1":
        slot = input(f"\n{YELLOW}Lunch slot? (e.g., Friday 1:30 PM): {RESET}").strip() or "Friday 1:30 PM"

        await agent_think("Dual-Diet Dineout Venue Discovery", [
            f"Scanning venues within 3.5km of {addr_obj['name']}.",
            f"Filtering places that have strong kitchens for BOTH {nv_pax} Non-Veg and {veg_pax} Veg guests.",
            f"Verifying live grill / dual buffet counters so vegetarian colleagues have fresh, dedicated grills."
        ])

        res = await mcp.call_tool("dineout", "search_dineout_venues", {
            "lat": addr_obj["lat"],
            "lng": addr_obj["lng"],
            "veg_count": veg_pax,
            "nv_count": nv_pax,
        })
        venues = res["venues"]

        table_rows = [
            [f"[{i}]", v["name"], f"* {v['rating']}", f"{v['dist_km']} km", v["cuisine"], v["veg_friendly_tag"], v["deal"]]
            for i, v in enumerate(venues, 1)
        ]

        print(tabulate(table_rows, headers=["#", "Venue", "Rating", "Distance", "Cuisine", "Veg & Non-Veg Experience", "Dineout Perk"], tablefmt="fancy_grid"))

        while True:
            choice = input(f"\n{YELLOW}Select a venue to reserve (1-{len(venues)}): {RESET}").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(venues):
                selected = venues[int(choice) - 1]
                break
            print(f"Please enter 1-{len(venues)}.")

        await agent_think("Atomic Table Reservation", [
            f"Locking {total_pax} seats at '{selected['name']}'.",
            f"Injecting dietary split metadata ({veg_pax} Veg, {nv_pax} Non-Veg) into table setup notes.",
            f"Confirming Dineout Pay offer '{selected['deal']}'."
        ])

        booking = await mcp.call_tool("dineout", "reserve_table", {
            "venue_name": selected["name"],
            "pax": total_pax,
            "veg_count": veg_pax,
            "nv_count": nv_pax,
            "slot": slot,
        })

        print("\n" + "=" * 68)
        print(f"{GREEN}{BOLD}[DINEOUT RESERVATION CONFIRMED]{RESET}")
        print(f"- {BOLD}Venue:{RESET}        {booking['venue']}")
        print(f"- {BOLD}Booking ID:{RESET}   {CYAN}{booking['booking_id']}{RESET}")
        print(f"- {BOLD}Total Seats:{RESET}  {booking['pax']} People ({booking['veg_split']})")
        print(f"- {BOLD}Slot:{RESET}         {booking['slot']}")
        print(f"- {BOLD}Special Deal:{RESET} {selected['deal']}")
        print("=" * 68)
        print(f"\n{CYAN}Last-minute change in team headcount?{RESET}")
        print("No worries at all, I will be right here! Just say 'Add 2 people' or 'Reschedule' anytime before the slot.\n")

    else:
        treat_time = input(f"\n{YELLOW}What time is lunch break at your office? (default: 1:15 PM): {RESET}").strip() or "1:15 PM"

        await agent_think("Dietary Balanced Menu Formulation", [
            f"Querying bulk kitchens delivering to {addr_obj['name']}.",
            f"Strict Constraint: Ensure {veg_pax} veg colleagues receive distinct primary dishes (not side orders).",
            f"Assembling dual packs: {nv_pax} Non-Veg handis + {veg_pax} dedicated Paneer/Veg handis + shared drinks."
        ])

        food_res = await mcp.call_tool("food", "search_dual_food_combos", {
            "veg_count": veg_pax,
            "nv_count": nv_pax,
        })
        combos = food_res["combos"]

        print(f"\n{BOLD}Curated Balanced Spreads for {total_pax} Colleagues ({nv_pax} NV + {veg_pax} Veg):{RESET}\n")
        for i, c in enumerate(combos, 1):
            nv_sum = sum(x["price"] for x in c["nv_items"])
            veg_sum = sum(x["price"] for x in c["veg_items"])
            drink_sum = c["drinks"]["price"]
            subtotal = nv_sum + veg_sum + drink_sum
            payable = subtotal - c["discount"]

            print(f"{CYAN}{BOLD}[{i}] {c['title']} - {c['restaurant']} (* {c['rating']}){RESET}")
            print(f"    {MAGENTA}Dietary Plan:{RESET} {c['tag']}")
            print(f"    {BOLD}Non-Veg Section ({nv_pax} pax):{RESET}")
            for x in c["nv_items"]:
                print(f"       - {x['name']} (Qty: {x['qty']}) - Rs.{x['price']}")
            print(f"    {BOLD}Dedicated Veg Section ({veg_pax} pax):{RESET}")
            for x in c["veg_items"]:
                print(f"       - {x['name']} (Qty: {x['qty']}) - Rs.{x['price']}")
            print(f"    {BOLD}Drinks:{RESET} {c['drinks']['name']} (Qty: {c['drinks']['qty']}) - Rs.{c['drinks']['price']}")
            print(f"    {BOLD}Total MRP:{RESET} Rs.{subtotal} | {GREEN}{BOLD}Payable with '{c['coupon']}': Rs.{payable}{RESET} (~Rs.{round(payable/total_pax)}/head)\n")

        while True:
            choice = input(f"{YELLOW}Select your base spread (1-{len(combos)}): {RESET}").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(combos):
                selected_combo = combos[int(choice) - 1]
                break
            print(f"Please enter 1-{len(combos)}.")

        # Instamart Post-Meal Chocolates / Celebrations
        await agent_think("Cross-Vertical Fulfillment (Instamart)", [
            "Checking team treat wrap-up items...",
            "Routing to Swiggy Instamart for chocolates and sweet celebrations suitable for everyone."
        ])

        im_res = await mcp.call_tool("im", "search_instamart_treats", {})
        treat_options = im_res["treats"]

        print(f"\n{CYAN}{BOLD}End your team treat with chocolates / sweet celebrations!{RESET}")
        print(f"{DIM}Quick delivery via Instamart straight to your office desk alongside lunch:{RESET}")
        for t_idx, t in enumerate(treat_options, 1):
            print(f" [{t_idx}] {t['name']} - Rs.{t['price']}")

        im_choice = input(f"\n{YELLOW}Add a sweet treat from Instamart? (1-{len(treat_options)} or 'N' for skip, default: 1): {RESET}").strip() or "1"
        added_treat = None
        if im_choice.isdigit() and 1 <= int(im_choice) <= len(treat_options):
            added_treat = treat_options[int(im_choice) - 1]
            print(f"{GREEN}[+] Added '{added_treat['name']}' (+Rs.{added_treat['price']}) to the celebration bag!{RESET}")

        # Final Cart Calculation
        nv_total = sum(x["price"] for x in selected_combo["nv_items"])
        veg_total = sum(x["price"] for x in selected_combo["veg_items"])
        drinks_total = selected_combo["drinks"]["price"]
        im_total = added_treat["price"] if added_treat else 0
        discount = selected_combo["discount"]
        final_payable = nv_total + veg_total + drinks_total + im_total - discount

        print("\n" + "=" * 68)
        print(f"{BOLD}FINAL TEAM SPREAD BREAKDOWN ({total_pax} People):{RESET}")
        for x in selected_combo["nv_items"]:
            print(f" - [Non-Veg] {x['name']} (Qty: {x['qty']}) - Rs.{x['price']}")
        for x in selected_combo["veg_items"]:
            print(f" - [Veg Safe] {x['name']} (Qty: {x['qty']}) - Rs.{x['price']}")
        print(f" - [Beverages] {selected_combo['drinks']['name']} - Rs.{drinks_total}")
        if added_treat:
            print(f" - [Instamart] {added_treat['name']} - Rs.{added_treat['price']}")
        print(f"\nSubtotal MRP:        Rs.{nv_total + veg_total + drinks_total + im_total}")
        print(f"Applied Coupon:      -Rs.{discount} ({selected_combo['coupon']})")
        print(f"{BOLD}Final Total Due:     Rs.{final_payable}{RESET}")
        print("=" * 68)

        confirm = input(f"\n{YELLOW}Lock order schedule for Friday at {treat_time}? (Y/N, default Y): {RESET}").strip().lower() or "y"
        if confirm == "y":
            await agent_think("Wallet Settlement & Background Queueing", [
                f"Validating user balance: Rs.{MOCK_USER_PROFILE['wallet_balance']}.",
                f"Debiting Rs.{final_payable} from Swiggy Money Wallet.",
                f"Scheduling delayed kitchen trigger for Day T at {treat_time} (minus 45 mins prep buffer)."
            ])

            pay_res = await mcp.call_tool("wallet", "debit_swiggy_wallet", {"amount": final_payable})

            print(f"\n{GREEN}{BOLD}[WALLET MONEY PAID SUCCESSFULLY]{RESET}")
            print(f"- Amount Debited:    {BOLD}Rs.{pay_res['amount_debited']}{RESET}")
            print(f"- Payment Mode:      {pay_res['payment_mode']}")
            print(f"- Transaction Ref:   {CYAN}{pay_res['txn_id']}{RESET}")
            print(f"- Remaining Balance: Rs.{pay_res['remaining_balance']}")
            print(f"- Birthday Cashback: {GREEN}+Rs.50 Swiggy Money credited!{RESET}")

            print(f"\n{YELLOW}[BACKGROUND SCHEDULER ACTIVE]{RESET} Order locked. Scheduled for {treat_time} delivery to {addr_obj['name']}.")
            print(f"{DIM}Sleeping until Day T (45 mins prior to {treat_time})...{RESET}")
            await asyncio.sleep(1.2)

            res = await mcp.call_tool("food", "fire_delayed_order", {"scheduled_time": treat_time})
            print(f"\n{GREEN}[ORDER AUTO-DISPATCHED TO KITCHEN & INSTAMART]{RESET}")
            print(f"- Food Order ID:      {BOLD}{res['order_id']}{RESET}")
            print(f"- Estimated Delivery: {BOLD}{res['delivery_eta']}{RESET}")

            print(f"\n{CYAN}{BOLD}Last-minute change of plans or sudden headcount shift?{RESET}")
            print(f"{BOLD}No worry, I will be here!{RESET} You can modify the headcount, swap veg items, or reschedule delivery anytime before dispatch--just ping me right here.\n")

if __name__ == "__main__":
    asyncio.run(main())
