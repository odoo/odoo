HR photo specs
==============

This revision modifies the photo for HR employees. Two fields now exist in the hr.employee model:
 - photo, a binary field holding the image
 - photo_mini, a binary field holding an automatically resized version of the avatar. Dimensions of the resized avatar are 180x150.

Employee photo should be used only when dealing with employees, using the photo_mini field. When dealing with users, use the res.users avatar_mini field instead.
