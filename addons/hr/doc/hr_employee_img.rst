HR photo specs
==============

This revision modifies the photo for HR employees. Two fields now exist in the hr.employee model:
 - photo_big, a binary field holding the image. It is base-64 encoded, and PIL-supported. It is automatically resized as an 540x450 px image.
 - photo, a functional binary field holding an automatically resized version of the photo. Dimensions of the resized photo are 180x150. This field is used as an inteface to get and set the employee photo.
When changing the photo through the photo function field, the new image is automatically resized to 540x450, and stored in the photo_big field. This triggers the function field, that will compute a 180x150 resized version of the image.

Employee photo should be used only when dealing with employees, using the photo field. When dealing with users, use the res.users avatar field instead.
