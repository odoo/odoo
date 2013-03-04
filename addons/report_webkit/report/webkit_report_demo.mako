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

    <p>The administrator name is: ${admin_name}</p>
    <p>If this report does not contain headers, it is because you have a badly compiled wkhtmltopdf. Consider installing
        the static version distributed on the official web site: <a href="https://code.google.com/p/wkhtmltopdf/">https://code.google.com/p/wkhtmltopdf/</a>.</p>
</body>
</html>