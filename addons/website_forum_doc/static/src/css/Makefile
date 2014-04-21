all: website_doc.css
%.css: %.sass
	sass -t expanded --compass --unix-newlines $< $@
watch:
	sass -t expanded --compass --unix-newlines --watch .:.
