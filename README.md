# Swiggy-bash



Built for the Swiggy Builders Club using Swiggy Food, Dineout, and Instamart MCP Servers.


In Indian tech hubs, organizing workplace birthday treats and family dinners involves significant friction:
- **Dietary Divide:** Vegetarian colleagues often get afterthought side dishes while non-veg eaters get full platters.
- **Logistical Complexity:** Stepping out requires immediate table reservations with verified seating; ordering in requires bulk cost calculations and delayed kitchen dispatch.
- **Cross-Vertical Needs:** Hot food alone is incomplete without post-meal sweets or chocolates.

**Swiggy Bash** solves this by acting as an autonomous concierge that connects contextual user profile data (DOB, saved address tags, historical taste graph) to Swiggy’s multi-vertical Model Context Protocol (MCP) tool suite.


Key Technical Highlights

1. **Dietary Parity Engine:**
   - Explicitly collects and respects the `Veg : Non-Veg` ratio.
   - Restructures food delivery queries around bulk handis/platters to bring per-head costs down from ₹400+ to ~₹200 without shortchanging vegetarian diners.
   - Filters Dineout venues specifically for isolated table grills or dedicated vegetarian counters (e.g., Barbeque Nation, AB's).

2. **Dual-Timeline Lifecycle Execution:**
   - **Immediate Execution:** Table locks via Dineout to eliminate venue seat dropouts.
   - **Delayed Execution:** Background job queue that stores the customized party cart and wakes up 45 minutes prior to treat time on Day T to verify real-time kitchen inventory and dispatch food.

3. **Multi-Vertical Chaining (Food + Dineout + Instamart):**
   - Automatically cross-sells contextual post-meal additions via Instamart: celebration chocolate gift packs for office floors vs. chilled rasmalai/ice creams for family tables.

4. **Transparent Thought Logs:**
   - Emits real-time reasoning steps (`[AGENT REASONING]`) illustrating how the agent resolves GPS coordinates, calculates portion weights, and chains MCP tools deterministically.
  
Tech Stack to try demo: 

- **Language:** Python 3.9+
- **Architecture:** Model Context Protocol (MCP) Client
- **Libraries:** `asyncio`, `tabulate`, `httpx`


Getting Started

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/swiggy-bash-copilot.git](https://github.com/your-username/swiggy-bash-copilot.git)
cd swiggy-bash-copilot


python3 -m venv venv
source venv/bin/activate

pip install tabulate httpx

python3 swiggy_bash.py
