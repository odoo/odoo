# OD19 Web Navigation Navbar Refresh Design

Date: 2026-11-05
Module: `od19_web_navigation`
Scope: Refine the Back / Forward navigation control so it feels native to the Odoo 19 navbar.

## Context

The current Back / Forward control works functionally, but its visual treatment reads like an overlay widget rather than a first-class navbar element. Because it sits immediately after the Home Menu, any mismatch in surface, spacing, radius, shadow, or hover language becomes obvious.

The goal is not to make the control more decorative. The goal is to make it feel like Odoo should have shipped it this way.

## Approved Direction

Approved design direction:

- Visual tone: `subtly refined`
- Composition: `single grouped control with divider`
- Placement: immediately after the Home Menu
- Principle: blend into the navbar first, then provide affordance second

This corresponds to the "Unified Segment" approach.

## Design Goals

1. Make the control feel native to the existing navbar.
2. Remove the floating "glass card" feeling.
3. Keep Back and Forward as a paired control.
4. Preserve current behavior and hotkeys.
5. Keep enough affordance that users still recognize it as an interactive navigation control.

## Non-Goals

1. No behavior changes to history tracking.
2. No relocation away from the Home Menu.
3. No new animation system or premium visual effects.
4. No backend/service refactor as part of the visual refresh.

## Recommended Approach

Replace the current pill-like glass surface with a flatter segmented control that inherits the navbar's visual language:

- one outer group container
- two icon buttons inside
- one thin divider between them
- minimal default background
- light hover and pressed states aligned with Odoo navbar items
- reduced radius and no pronounced shadow

This keeps the control discoverable without making it compete with the Apps Menu or app brand.

## Visual Specification

### Container

- Height should visually align with surrounding navbar entries.
- Border radius should be smaller than the current pill treatment.
- Default background should be transparent or near-transparent.
- Border should be faint and structural, not decorative.
- No heavy blur or elevated floating effect.
- No visible drop shadow in resting state.

### Buttons

- Back and Forward remain equal-width icon buttons.
- Internal spacing should be tighter and more aligned to navbar density.
- Icons should look crisp, centered, and slightly calmer than the current implementation.
- Button hover should use the same family of feedback as Odoo navbar entries: soft background shift, no lift.
- Active state should feel firm but shallow, with no bouncing or floating illusion.

### Divider

- A thin vertical divider separates Back and Forward.
- Divider is always visible but low contrast.
- Divider should reinforce the idea of "one control, two actions".

### Disabled State

- Forward disabled state should remain clearly inactive.
- Disabled state should lower contrast, but preserve layout and alignment.
- Disabled controls should not collapse or visually disappear.

## Interaction Specification

Behavior remains unchanged:

- Back goes to previous tracked state.
- If there is no tracked history, Back goes to the current app home.
- Forward becomes active only when a future tracked state exists.
- Hotkeys remain `Alt+Left` and `Alt+Right`.

## Technical Design

### Files in Scope

- `custom_addons/od19_web_navigation/static/src/js/od19_nav_buttons.js`
- `custom_addons/od19_web_navigation/static/src/css/od19_nav_buttons.css`

### Expected Markup Changes

The component markup may be adjusted slightly to support:

- a named outer group container
- a dedicated divider element
- button classes that better map to segmented styling

No template inheritance changes are needed unless the current structure blocks consistent styling.

### Styling Strategy

Update only module-local CSS. Do not modify Odoo core navbar styles.

The refreshed styles should:

- inherit navbar color naturally
- avoid custom visual language that fights the host navbar
- keep selectors scoped to `od19_web_navigation`

## Alternatives Considered

### 1. Keep the current glass pill and tune it down

Pros:

- smallest visual diff
- preserves current implementation shape

Cons:

- still reads as a foreign widget
- blur and shadow remain visually separate from the navbar system

### 2. Unified segmented control

Pros:

- strongest fit with existing navbar
- clean grouping of Back / Forward
- refined without calling attention to itself

Cons:

- less visually expressive than a premium pill treatment

### 3. Back-first asymmetric control

Pros:

- emphasizes the action users likely use more

Cons:

- weakens the conceptual pairing of Back / Forward
- more likely to look custom rather than native

## Why This Approach

The navbar is already visually busy with app switcher, app name, breadcrumbs, sections, and systray items. A control inserted this early in the hierarchy must defer to the host design system. The segmented approach does that best: it gives structure, clarity, and recognizability without introducing a competing material language.

## Validation Criteria

The refresh is successful when:

1. the control no longer looks like a floating widget;
2. it visually belongs beside the Home Menu;
3. the Back / Forward affordance remains obvious;
4. the navbar does not feel heavier after the change;
5. disabled Forward still looks intentional and readable.

## Testing Notes

Validation should include:

1. visual check on normal desktop width;
2. hover and active state check;
3. disabled Forward state check;
4. confirmation that Back still returns to app home when no history exists;
5. confirmation that frontend and backend assets remain healthy after update.

## Risks

1. Over-softening the control could make it disappear next to the Apps Menu.
2. Reusing too much of the navbar language could make button hit areas feel too small.
3. Asset cache can obscure visual changes, so hard refresh may still be needed during verification.

## Implementation Summary

Implement a restrained segmented navigation control that sits after the Home Menu and visually integrates with the Odoo navbar through flatter surfaces, tighter spacing, a subtle divider, and native-feeling hover/pressed states while keeping current behavior unchanged.
