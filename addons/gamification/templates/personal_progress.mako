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
            <td>${goal.target_goal}
            % if goal.type_suffix:
                ${goal.type_suffix}
            % endif
            </td>
            <td>${goal.current}
            % if goal.type_suffix:
                ${goal.type_suffix}
            % endif
            </td>
            <td>${goal.completeness} %</td>
        </tr>
    % endfor
    </table>
<% endblock %>