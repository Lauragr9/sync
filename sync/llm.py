import os
import json
import re
from groq import Groq


def get_real_places(client, destination, budget):
    """First pass: ask the model to commit to a verified list of real venues."""
    prompt = f"""You are a travel expert with deep local knowledge of {destination}.

List real, existing venues in {destination} that suit a {budget} budget.
Only include places you are certain exist — do not guess or invent names.

Return ONLY raw JSON, no markdown, no code blocks:

{{
  "restaurants": [
    {{"name": "Exact restaurant name", "type": "cuisine type", "note": "one known fact"}}
  ],
  "hotels": [
    {{"name": "Exact hotel name", "neighbourhood": "area", "note": "one known fact"}}
  ],
  "attractions": [
    {{"name": "Exact place name", "type": "museum/park/landmark/etc", "note": "one known fact"}}
  ]
}}

Include: 10 restaurants, 5 hotels, 10 attractions. Only real places you are highly confident about."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    raw = response.choices[0].message.content
    clean = re.sub(r'```json|```', '', raw).strip()
    start = clean.find('{')
    end = clean.rfind('}') + 1
    return json.loads(clean[start:end])


def generate_itinerary(trip, proposal):
    destination = f"{proposal.city}, {proposal.country}"

    if trip.departure_date and trip.return_date:
        nights = (trip.return_date - trip.departure_date).days
    else:
        nights = 3

    display_nights = min(nights, 5)
    members_count = trip.members.count()
    budget = trip.get_budget_range_display()

    client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

    print(f"Pass 1: fetching real venues for {destination}...")
    try:
        places = get_real_places(client, destination, budget)
        restaurants = [f"{p['name']} ({p.get('type', '')} — {p.get('note', '')})" for p in places.get('restaurants', [])]
        hotels = [f"{p['name']} in {p.get('neighbourhood', '')} — {p.get('note', '')}" for p in places.get('hotels', [])]
        attractions = [f"{p['name']} ({p.get('type', '')} — {p.get('note', '')})" for p in places.get('attractions', [])]

        places_block = f"""Verified real places in {destination} — use ONLY these:

Restaurants/cafés:
{chr(10).join(f'- {r}' for r in restaurants)}

Hotels:
{chr(10).join(f'- {h}' for h in hotels)}

Attractions/museums/parks:
{chr(10).join(f'- {a}' for a in attractions)}

Do not use any place not on these lists."""
    except Exception as e:
        print(f"Pass 1 failed: {e} — falling back to single pass")
        places_block = f"Use only real, well-known, verifiably existing places in {destination}. Do not invent venue names."

    print(f"Pass 2: generating itinerary for {destination}...")
    prompt = f"""You are a local travel planner for {destination}. Generate a day-by-day itinerary in JSON.

Trip details:
- Destination: {destination}
- Duration: {display_nights} nights
- Group size: {members_count} people
- Budget: {budget}
- Departure: {trip.departure_date}

{places_block}

Rules:
- Every food activity must name a real restaurant or café from the list above
- Every accommodation activity must name a real hotel from the list above
- Every sightseeing activity must name a real attraction from the list above
- Maximum 3 activities per day
- Each description must be one sentence mentioning a specific detail (what it's known for, a dish, an opening tip, etc.)
- Return ONLY raw JSON, no markdown, no code blocks
- Start with {{ and end with }}

{{
  "days": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "location": "Neighbourhood or area",
      "theme": "Short theme",
      "activities": [
        {{
          "time_slot": "09:00",
          "title": "Real place name — what you will do",
          "description": "One sentence with a specific detail about this exact place.",
          "category": "activity"
        }}
      ]
    }}
  ]
}}

Categories: transport, food, activity, accommodation, free"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
    )

    raw = response.choices[0].message.content
    clean = re.sub(r'```json|```', '', raw).strip()
    start = clean.find('{')
    end = clean.rfind('}') + 1
    clean = clean[start:end]

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {e}, trying again...")
        fix_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "Fix the JSON syntax error. Return ONLY the corrected JSON, nothing else."}
            ],
            max_tokens=3000,
        )
        raw2 = fix_response.choices[0].message.content
        clean2 = re.sub(r'```json|```', '', raw2).strip()
        start2 = clean2.find('{')
        end2 = clean2.rfind('}') + 1
        data = json.loads(clean2[start2:end2])

    return data, raw
