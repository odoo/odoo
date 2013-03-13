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

    % if badge.image
        <p><img src="cid:badge-img.png" alt="Badge ${badge.name}" /></p>
    % endif
    % if badge.description
        <p><em>${badge.description}</em></p>
    % endif
  </body>
</html>