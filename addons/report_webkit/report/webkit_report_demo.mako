<!DOCTYPE html>
<html>
<head>
    <style type="text_css">${css}</style>
</head>
<body>
    <h1>List of reports:</h1>
    <ul>
    % for report in objects:
        <li>${report.name}</li>
    % endfor
    </ul>
</body>
</html>