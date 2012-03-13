User avatar
===========

This revision adds an avatar for users. This replace the use of gravatar to emulate avatars, such as used in tasks kanban view. Two fields are added to res.users model:
- avatar, binary image
- avatar_mini, an automatically computed reduced version of the avatar
User avatar has to be used everywhere an image depicting users is likely to be used, by using the avatar_mini field.

Avatar choice has been added to the users form view, as well as in Preferences.
