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
<% block body %><% endblock %>

</body>