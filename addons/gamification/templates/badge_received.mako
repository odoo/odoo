<!DOCTYPE html>
<html>
  <head>
    <style type="text_css">${css}</style>
  </head>
  <body>
    <p>Congratulation, you have received the badge <strong>${badge.name}</strong> !
        % if user_from
            This badge was granted by <strong>${user_from.name}</strong>.
        % endif
    </p>

	  <p><img src="data:image/png;base64,${badgeb64}" alt="badge ${badge.name}" /></p>

    <p><em>${description}</em></p>
    
  </body>
</html>