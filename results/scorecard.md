# Agent Ops Bench — Comparison Scorecard

Subset: 30 hard-case-weighted tickets (see data/subset.json).

| Config | Severity | Routing | P1 catch | Under-triage | Cost/ticket | Avg latency |
|---|---|---|---|---|---|---|
| Generalist (1 call) | 21/30 (70%) | 25/30 (83%) | 6/7 | 5 | $0.080 | 5.1s |
| Specialists (2 calls) | 21/30 (70%) | 29/30 (97%) | 7/7 | 5 | $0.149 | 5.2s |
| Generalist + QA (2 calls) | 24/30 (80%) | 27/30 (90%) | 7/7 | 6 | $0.160 | 10.4s |

## QA Reviewer Economics (Config C)

- Overrides issued: 9/30
- Catches (fixed a first-pass error): 6 — T007, T014, T029, T030, T059, T060
- Harms (broke a correct first-pass call): 2 — T012, T028
- Added cost vs. Config A: $0.080/ticket
- Net corrections: +4 — reviewer cost per net correction: $0.60

## Misses — Generalist (1 call) (13)

- T006: routing "Field Service / Hardware Dispatch"->"Access Control & Security" — "Front gate and lobby access panel both show offline in the dashboard as of 7am. ..."
- T014: severity P2->P1 — "My unit's lock keeps saying 'device unreachable' when I try to lock or unlock fr..."
- T018: severity P2->P3 — "App keeps saying my lock is 'low battery critical' and won't let me lock remotel..."
- T020: severity P2->P1; routing "Field Service / Hardware Dispatch"->"Access Control & Security" — "Access panel at the pool gate not responding to any resident fobs or the app, po..."
- T029: severity P3->P2 — "Had an app lock issue yesterday evening, used my keypad code as backup and got i..."
- T030: severity P3->P2 — "Resident in 112 reported being locked out last night, our office confirmed they ..."
- T036: routing "Tier 1 Support"->"Access Control & Security" — "Is there a way to give my dog walker a temporary door code that expires after a ..."
- T050: severity P3->P4 — "App crashes every single time I try to open the energy usage tab, happens consis..."
- T051: routing "Product/Engineering Bug Report"->"Access Control & Security" — "Push notifications for lock activity stopped coming through about a week ago, ap..."
- T053: routing "Product/Engineering Bug Report"->"Tier 1 Support" — "Dark mode setting keeps reverting to light mode every time I close and reopen th..."
- T054: severity P2->P3 — "Community room thermostat is offline, room isn't in use this week so no rush, bu..."
- T055: severity P3->P4 — "Gym access panel let me in fine today but the app still shows it as 'offline' fr..."
- T060: severity P1->P2 — "Resident in 407 says their front door lock has not responded to app, keypad, or ..."

## Misses — Specialists (2 calls) (9)

- T014: severity P2->P1 — "My unit's lock keeps saying 'device unreachable' when I try to lock or unlock fr..."
- T018: severity P2->P3 — "App keeps saying my lock is 'low battery critical' and won't let me lock remotel..."
- T020: severity P2->P3; routing "Field Service / Hardware Dispatch"->"Access Control & Security" — "Access panel at the pool gate not responding to any resident fobs or the app, po..."
- T029: severity P3->P2 — "Had an app lock issue yesterday evening, used my keypad code as backup and got i..."
- T030: severity P3->P2 — "Resident in 112 reported being locked out last night, our office confirmed they ..."
- T050: severity P3->P4 — "App crashes every single time I try to open the energy usage tab, happens consis..."
- T051: severity P3->P2 — "Push notifications for lock activity stopped coming through about a week ago, ap..."
- T054: severity P2->P3 — "Community room thermostat is offline, room isn't in use this week so no rush, bu..."
- T055: severity P3->P4 — "Gym access panel let me in fine today but the app still shows it as 'offline' fr..."

## Misses — Generalist + QA (2 calls) (9)

- T006: routing "Field Service / Hardware Dispatch"->"Access Control & Security" — "Front gate and lobby access panel both show offline in the dashboard as of 7am. ..."
- T012: severity P2->P3 — "Bedroom thermostat shows offline in the app, has been since yesterday. Can't adj..."
- T018: severity P2->P3 — "App keeps saying my lock is 'low battery critical' and won't let me lock remotel..."
- T020: routing "Field Service / Hardware Dispatch"->"Access Control & Security" — "Access panel at the pool gate not responding to any resident fobs or the app, po..."
- T028: severity P2->P3 — "I got locked out this morning but used the backup keypad code and got in fine. J..."
- T050: severity P3->P4 — "App crashes every single time I try to open the energy usage tab, happens consis..."
- T051: routing "Product/Engineering Bug Report"->"Access Control & Security" — "Push notifications for lock activity stopped coming through about a week ago, ap..."
- T054: severity P2->P3 — "Community room thermostat is offline, room isn't in use this week so no rush, bu..."
- T055: severity P3->P4 — "Gym access panel let me in fine today but the app still shows it as 'offline' fr..."
