import os
import json
import re
from groq import Groq

def generate_itinerary(trip):
    winner = trip.proposals.first()
    destination = f"{winner.city}, {winner.country}" if winner else "destination TBD"

    if trip.departure_date and trip.return_date:
        nights = (trip.return_date - trip.departure_date).days
    else:
        nights = 3

    members_count = trip.members.count()

    client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

    prompt = f"""You are a travel planner. Generate a detailed day-by-day itinerary in JSON.

Trip details:
- Destination: {destination}
- Duration: {nights} nights
- Group size: {members_count} people
- Budget: {trip.get_budget_range_display()}
- Departure: {trip.departure_date}
- Return: {trip.return_date}

Return ONLY a JSON object with this exact structure, no extra text, no markdown:
{{
  "days": [
    {{
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "location": "City name",
      "theme": "One short theme line",
      "activities": [
        {{
          "time_slot": "09:00",
          "title": "Activity name",
          "description": "2-3 sentences about this activity",
          "category": "activity"
        }}
      ]
    }}
  ]
}}

Categories must be one of: transport, food, activity, accommodation, free"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
    )

    raw = response.choices[0].message.content
    clean = re.sub(r'```json|```', '', raw).strip()
    data = json.loads(clean)
    return data, raw