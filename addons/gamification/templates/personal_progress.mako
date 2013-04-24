<% extends 'base.mako' %>

<% block body %><table width="100%" border="1">
    <tr>
        <th>Goal</th>
        <th>Target</th>
        <th>Current</th>
        <th>Completeness</th>
    </tr>
    % for goal in goals:
        <tr
            % if goal.completeness >= 100:
                style="font-weight:bold;"
            % endif
            >
            <td>${goal.type_id.name}</td>
            <td>${goal.target_goal} ${goal.type_suffix}</td>
            <td>${goal.current} ${goal.type_suffix}</td>
            <td>${goal.completeness} %</td>
        </tr>
    % endfor
    </table>
<% endblock %>