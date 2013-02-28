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

    % for planline in planlines_boards:
        
        <table width="100%" border="1">
        	<tr>
        		<th colspan="4">${planline['goal_type']}</th>
        	</tr>
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

        <br/><br/>

    % endfor
</body>