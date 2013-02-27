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
    
    Below are the latest results for the plan <strong>${object.name}</strong> for the group <em>${object.report_message_group_id.name}</em>.</p>
    !${planlines_boards}!
    % for planline in planlines_boards:
        <h2>${planline['goal_type']}</h2>
        <table width="100%" border="1">
        	<tr>
	            <th>#</th>
	            <th>User</th>
	            <th>Completeness</th>
	            <th>Current</th>
	        </tr>
	        % for idx, goal in planline['board_goals']:
	            <tr
	                % if goal.completeness >= 100:
	                    style="font-weight:bold;"
	                % endif
	                >
	                <td>${idx+1}</td>
	                <td>${goal.user.name}</td>
	                <td>${goal.completeness}%</td>
	                <td>${goal.current}/${goal.target_goal}</td>
	            </tr>
	        % endfor
        </table>
    % endfor
</body>