# Fire alert check: guide for annotators

You will look at satellite images of places where a satellite detected a fire and say what you think caused it. No special knowledge is needed beyond this guide. Work alone, do not look up news about the places, and do not discuss individual alerts with other annotators until everyone has finished.

## Each alert (about 3 minutes)
1. Look at the BEFORE and AFTER Sentinel-2 true-colour images and the BLINK panel. A change inside the yellow ring (1 km around the alert point) is the clue: a new dark patch (burn scar), smoke or an active fire. If an image is cloudy near the point, use the arrows for another date.
2. Use the 3x close-up panels for small changes. They add no detail, only larger pixels.
3. Look at the ground views, if present: field, grass or forest, houses, or a factory.
4. Fill in: fire_or_burn_visible (yes / no / cannot_tell), land_context (cropland / forest_grass / built_up / industrial / other), likely_cause, confidence (low / medium / high), and an optional one-line note.

## Likely cause (exactly one)
| Cause | Look for |
|---|---|
| agricultural | burn with straight edges on a field |
| wildfire | ragged burn in grass, reeds, scrub or forest |
| industrial_static | a factory, depot, flare or landfill; no change between dates |
| military | craters, destroyed buildings, burning vehicles, a pattern of strikes (a burn alone is not enough) |
| unclear | the images do not decide it |

## Rules
- Use `unclear` whenever you are not sure. A wrong guess is worse than an honest "unclear".
- If you cannot decide in 5 minutes, write `unclear` and move on.
- Work in order and do not go back to change answers after seeing later alerts.
- Do not look at or ask for any answer key.
- When finished, click "Export CSV" once and send the file to the person who gave you the page.
