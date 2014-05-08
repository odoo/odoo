all: *.css
%.css: %.sass
	sass -t expanded --unix-newlines $< $@
watch:
	sass -t expanded --unix-newlines --watch .:.
