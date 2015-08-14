DOTFILES:=$(wildcard *.dot)
SVGFILES:=$(patsubst %.dot,%.svg,$(DOTFILES))
PNGFILES:=$(patsubst %.dot,%.png,$(DOTFILES))

# try to disable implicit rules
.SUFFIXES:

.PHONY: all clean

all: $(SVGFILES) $(PNGFILES)

# must -f to ignore errors when running clean multiple times in a row
clean:
	rm -f *.png *.svg

%.svg: %.dot
	dot -Tsvg $< > $@

%.png: %.dot
	dot -Tpng $< > $@
