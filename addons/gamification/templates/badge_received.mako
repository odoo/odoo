<!DOCTYPE html>
<html>
  <head>
    <style type="text_css">${css}</style>
  </head>
  <body>
    <p>Congratulation, you have received the badge <strong>${badge_user.badge_id.name}</strong> !
        % if user_from
            This badge was granted by <strong>${user_from.name}</strong>.
        % endif
    </p>

    % if badge_user.badge_id.image
        <p><img src="cid:badge-img.png" alt="Badge ${badge_user.badge_id.name}" /></p>
    % endif
    % if badge_user.comment
        <p><em>${badge_user.comment}</em></p>
    % endif
  </body>
</html>