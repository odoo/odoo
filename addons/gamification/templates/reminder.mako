<!DOCTYPE html>
<html>
<head>
    <style type="text_css">${css}</style>
</head>
<body>
	<header>
	    <strong>Reminder ${object.name}</strong>
	</header>

	<p class="oe_grey">${object.report_header or ''}</p>
    
    <p>You have not updated your progress for the goal ${object.definition_id.name} (currently reached at ${object.completeness}%) for at least ${object.remind_update_delay} days. Do not forget to do it.</p>

    <p>If you have not changed your score yet, you can use the button "The current value is up to date" to indicate so.</p>
</body>
</html>
