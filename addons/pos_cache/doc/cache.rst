POS Cache
+++++++++

This module enables a cache for the products in the pos configs. Each POS Config has his own Cache.

The Cache is updated every hour by a cron.

============
Compute user
============

As it's a bad practice to use the admin in a multi-company configuration, a field permit to force a user to compute
the cache. A badly chosen user can result in wrong taxes in POS in a multi-company environment.
