This module extends the web module to add new dashboard overview system.

By default, the tile displays items count of a given model restricted to a given domain.

Optionally, the tile can display the result of a function on a field.

- Function is one of ``sum``, ``avg``, ``min``, ``max`` or ``median``.
- Field must be integer or float.

Tile can be:

- Displayed only for a user.
- Global for all users.
- Restricted to some groups.

*Note: The tile will be hidden if the current user doesn't have access to the given model.*
