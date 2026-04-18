# Sync — database structure

## Tables overview

| Table | Purpose |
|---|---|
| `Trip` | The core trip object — name, dates, budget, invite link |
| `TripMember` | Links users to trips (who is in which trip) |
| `DestinationProposal` | A destination someone proposes for the trip |
| `Vote` | A user's vote on a destination proposal |
| `Availability` | Whether a user is available on a given date |
| `Itinerary` | The AI-generated itinerary for a trip |
| `ItineraryDay` | One day within an itinerary |
| `ItineraryActivity` | One activity within a day |
| `PackingItem` | An item on the group packing list |

---

## Table details

### Trip
The central table. Everything else connects back to a Trip.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key, auto-generated |
| `name` | CharField | e.g. "Christmas in Paris" |
| `slug` | SlugField | URL-friendly name, e.g. `christmas-in-paris` — must be unique |
| `description` | TextField | Optional description |
| `status` | CharField | `planning` / `confirmed` / `completed` |
| `departure_date` | DateField | Optional |
| `return_date` | DateField | Optional |
| `budget_range` | CharField | `budget` / `mid` / `luxury` |
| `invite_token` | UUIDField | Random unique token for the invite link |
| `lead` | FK → User | The person who created the trip |
| `members` | M2M → User | Via TripMember (see below) |
| `created_at` | DateTimeField | Auto-set on creation |

---

### TripMember
The join table between Trip and User. Every person in a trip has a row here.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `trip` | FK → Trip | Which trip |
| `user` | FK → User | Which user |
| `role` | CharField | `lead` or `member` |
| `joined_at` | DateTimeField | Auto-set on creation |

> **Constraint:** `unique_together = ('trip', 'user')` — a user can only be in a trip once.

---

### DestinationProposal
A destination that someone has suggested for the trip. A trip can have multiple proposals.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `trip` | FK → Trip | Which trip this proposal belongs to |
| `proposed_by` | FK → User | Who suggested it (nullable) |
| `city` | CharField | e.g. "Barcelona" |
| `country` | CharField | e.g. "Spain" |
| `notes` | TextField | Optional — why they're suggesting it |
| `created_at` | DateTimeField | Auto-set |

---

### Vote
A user's vote on a destination proposal.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `proposal` | FK → DestinationProposal | Which proposal |
| `user` | FK → User | Who voted |
| `score` | IntegerField | `1` = Yes, `0` = Maybe, `-1` = No |

> **Constraint:** `unique_together = ('proposal', 'user')` — one vote per user per proposal.

---

### Availability
One row per user per date per trip. Tracks who can make which dates.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `trip` | FK → Trip | Which trip |
| `user` | FK → User | Which user |
| `date` | DateField | The specific date |
| `status` | CharField | `available` / `maybe` / `unavailable` |

> **Constraint:** `unique_together = ('trip', 'user', 'date')` — one status per user per date per trip.

---

### Itinerary
The AI-generated itinerary for a trip. One itinerary per trip (OneToOne).

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `trip` | OneToOne → Trip | One itinerary per trip |
| `llm_raw` | TextField | The raw JSON response from the LLM |
| `status` | CharField | `pending` / `generating` / `ready` / `failed` |
| `generated_at` | DateTimeField | When the LLM finished |

---

### ItineraryDay
One day within an itinerary.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `itinerary` | FK → Itinerary | Which itinerary |
| `day_number` | PositiveIntegerField | 1, 2, 3... |
| `date` | DateField | The actual calendar date |
| `location` | CharField | City or area for the day |
| `theme` | CharField | Optional — e.g. "Museums and culture" |

> **Ordering:** by `day_number` automatically.

---

### ItineraryActivity
One activity within a day (a meal, a visit, transport, etc).

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `day` | FK → ItineraryDay | Which day |
| `time_slot` | CharField | e.g. "09:00" |
| `title` | CharField | e.g. "Visit the Eiffel Tower" |
| `description` | TextField | Optional longer description |
| `category` | CharField | `transport` / `food` / `activity` / `accommodation` / `free` |

> **Ordering:** by `time_slot` automatically.

---

### PackingItem
An item on the group packing list. Can be claimed by one person.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `trip` | FK → Trip | Which trip |
| `claimed_by` | FK → User | Who is bringing it (nullable) |
| `name` | CharField | e.g. "First aid kit" |
| `category` | CharField | Optional — e.g. "Medical" |
| `is_packed` | BooleanField | False by default |



## Key rules to remember

- **Never use `trip.members.add()`** — because members is a ManyToMany through TripMember, you must create `TripMember` objects directly.
- **Votes are unique per user per proposal** — use `update_or_create` when saving a vote, never bare `create()`.
- **Availability is unique per user per date per trip** — same rule, use `update_or_create`.
- **Itinerary is OneToOne with Trip** — there can only ever be one itinerary per trip.
- **Slug must be unique** — auto-generate it with `slugify(trip.name)` in the view, never ask the user to type it.
