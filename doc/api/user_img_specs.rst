User avatar
===========

This revision adds an avatar for users. This replaces the use of gravatar to emulate avatars, used in views like the tasks kanban view. Two fields have been added to the res.users model:
 - avatar, a binary field holding the image
 - avatar_mini, a binary field holding an automatically resized version of the avatar. Dimensions of the resized avatar are 180x150.
User avatar has to be used everywhere an image depicting users is likely to be used, by using the avatar_mini field.

An avatar field has been added to the users form view, as well as in Preferences. When creating a new user, a default avatar is chosen among 6 possible default images.
