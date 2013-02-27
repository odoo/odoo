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
    
    <p>You have not updated your progress for the goal ${object.type_id.name} (currently reached at ${object.completeness}%) for at least ${object.remind_update_delay}. Do not forget to do it.</p>

    <p>If you have not changed your score yet, you can use the button "The current value is up to date" to indicate so.</p>
</body>