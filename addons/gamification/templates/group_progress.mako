<% extends 'base.mako' %>

<% block body %>
	% for line in lines_boards: 
        <table width="100%" border="1">
        	<tr>
        		<th colspan="4">${line.goal_definition.name}</th>
        	</tr>
        	<tr>
	            <th>#</th>
	            <th>Person</th>
	            <th>Completeness</th>
	            <th>Current</th>
	        </tr>
	        % for idx, goal in line.board_goals:
                % if idx < 3 or goal.user_id.id == uid:
    	            <tr
    	                % if goal.completeness >= 100:
    	                    style="font-weight:bold;"
    	                % endif
    	                >
    	                <td>${idx+1}</td>
    	                <td>${goal.user_id.name}</td>
    	                <td>${goal.completeness}%</td>
    	                <td>${goal.current}/${goal.target_goal}
                        % if goal.definition_suffix:
                            ${goal.definition_suffix}
                        % endif
                        </td>
    	            </tr>
                % endif
	        % endfor
        </table>

        <br/><br/>

    % endfor
<% endblock %>