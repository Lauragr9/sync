import os
import json
import re
from groq import Groq

def generate_itinerary(trip, proposal):
    destination = f"{proposal.city}, {proposal.country}"

    if trip.departure_date and trip.return_date:
        nights = (trip.return_date - trip.departure_date).days
    else:
        nights = 3

    display_nights = min(nights, 5)
    members_count = trip.members.count()

    client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

    prompt = f"""You are a travel planner. Generate a day-by-day itinerary in JSON.

Trip details:
- Destination: {destination}
- Duration: {display_nights} nights
- Group size: {members_count} people
- Budget: {trip.get_budget_range_display()}
- Departure: {trip.departure_date}

Rules:
- Maximum 3 activities per day
- Keep descriptions to 1 sentence only
- Return ONLY raw JSON, no markdown, no code blocks
- Start with {{ and end with }}

{{
  "days": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "location": "City name",
      "theme": "Short theme",
      "activities": [
        {{
          "time_slot": "09:00",
          "title": "Activity name",
          "description": "One sentence.",
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
        max_tokens=2000,
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
            max_tokens=2000,
        )
        raw2 = fix_response.choices[0].message.content
        clean2 = re.sub(r'```json|```', '', raw2).strip()
        start2 = clean2.find('{')
        end2 = clean2.rfind('}') + 1
        data = json.loads(clean2[start2:end2])

    return data, raw