<!DOCTYPE html>
<html>
<head>
    <style type="text_css">${css}</style>
</head>
<body>
	<header>
        <strong>${object.name}</strong>
    </header>

    <p class="oe_grey">${object.report_header or ''}</p>
    <br/><br/>
    <table width="100%" border="1">
    <tr>
        <th>Goal</th>
        <th>Target</th>
        <th>Current</th>
        <th>Completeness</th>
    </tr>
    % for goal in goals:
        <tr>
            <td>${goal.type_id.name}</td>
            <td>${goal.target_goal}</td>
            <td>${goal.current}</td>
            <td>${goal.completeness} %</td>
        </tr>

        <br/><br/>  
    
    % endfor
    </table>
</body>