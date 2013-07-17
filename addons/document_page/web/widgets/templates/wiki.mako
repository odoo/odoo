% if editable and not inline:
    <textarea rows="10" id="${name}" name="${name}" class="${css_class}"
        ${py.attrs(attrs, kind=kind)} style="width: 99%;">${value}</textarea>
    <script type="text/javascript">
        if (!window.browser.isWebKit) {
            new openerp.ui.TextArea('${name}');
        }
    </script>
% endif

% if editable and inline:
    <input type="text" id="${name}" name="${name}" class="${css_class}"
        ${py.attrs(attrs, kind=kind, value=value)}/>
% endif
    
% if editable and error:
    <span class="fielderror">${error}</span>
% endif

% if not editable and value:
    <div kind="${kind}" id="${name}" class="${css_class}">${data|n}</div>
% endif

