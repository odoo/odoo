<% extends 'base.mako' %>

<% block body %><table width="100%" border="1">
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
<% endblock %>