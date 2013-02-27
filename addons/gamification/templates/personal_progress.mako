<!DOCTYPE html>
<html>
<head>
    <style type="text_css">${css}</style>
</head>
<body>
	<header>
	    % if object.report_header
	    	${object.report_header}
	    % endif
	</header>
    
    <p>Below are the latest results for the plan ${object.name} for ${user.name}.</p>

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
    % endfor
    </table>
</body>