User avatar
===========

This revision adds an avatar for users. This replaces the use of gravatar to emulate avatars, used in views like the tasks kanban view. Two fields have been added to the res.users model:
 - avatar_stored, a binary field holding the image. It is base-64 encoded, and PIL-supported. Images stored are resized to 540x450 px, to limitate the binary field size.
 - avatar, a function binary field holding an automatically resized version of the avatar_stored field. Dimensions of the resized avatar are 180x150. This field is used as an inteface to get and set the user avatar. When changing this field in a view, the new image is automatically resized, and stored in the avatar_stored field. Note that the value is stored on another field, because otherwise it would imply to write on the function field, which currently using OpenERP 6.1 can lead to issues.
User avatar has to be used everywhere an image depicting users is likely to be used, by using the avatar field.

An avatar field has been added to the users form view, as well as in Preferences. When creating a new user, a default avatar is chosen among 6 possible default images.
