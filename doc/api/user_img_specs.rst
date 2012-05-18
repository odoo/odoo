User avatar
===========

.. versionadded:: 7.0

This revision adds an avatar for users. This replaces the use of gravatar to emulate avatars, used in views like the tasks kanban view. Two fields have been added to the res.users model:
 - avatar_big, a binary field holding the image. It is base-64 encoded, and PIL-supported. Images stored are resized to 540x450 px, to limitate the binary field size.
 - avatar, a function binary field holding an automatically resized version of the avatar_big field. It is also base-64 encoded, and PIL-supported. Dimensions of the resized avatar are 180x150. This field is used as an inteface to get and set the user avatar.
When changing the avatar through the avatar function field, the new image is automatically resized to 540x450, and stored in the avatar_big field. This triggers the function field, that will compute a 180x150 resized version of the image.

An avatar field has been added to the users form view, as well as in Preferences. When creating a new user, a default avatar is chosen among 6 possible default images.
