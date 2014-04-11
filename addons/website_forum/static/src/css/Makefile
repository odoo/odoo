all: website_forum.css
%.css: %.sass
	sass -t expanded --compass --unix-newlines $< $@
watch:
	sass -t expanded --compass --unix-newlines --watch .:.
