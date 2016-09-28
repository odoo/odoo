with import <nixpkgs> {}; {
  pyEnv = stdenv.mkDerivation {
    shellHook = ''
      #LIBRARY_PATH="${libxml2}/lib";
      export LD_LIBRARY_PATH="/var/run/current-system/sw/lib:${libjpeg}/lib:$LD_LIBRARY_PATH"
      # ditto for header files, e.g. sqlite
      export C_INCLUDE_PATH=/var/run/current-system/sw/include

      npm install less less-plugin-clean-css
      export PATH="$(pwd)/node_modules/less/bin:$PATH"
      export NODE_PATH="$(pwd)/node_modules:$NODE_PATH"
      source ${python27Packages.virtualenvwrapper}/bin/virtualenvwrapper.sh

      npm install typescript
      export PATH="$(pwd)/node_modules/typescript/bin:$PATH"

      npm install immutable      
      '';
    name = "odoo-9.0";
    buildInputs = [
      git
      nodejs
      
      stdenv
      python27Full
      python27Packages.virtualenv
      python27Packages.virtualenvwrapper
      libxml2

    ];
    propagatedBuildInputs = [
      docutils
      python27Packages.Babel
      python27Packages.Mako
      python27Packages.argparse
      python27Packages.dateutil_1_5
      python27Packages.decorator
      python27Packages.feedparser
      python27Packages.gdata
      python27Packages.gevent
      python27Packages.greenlet
      python27Packages.jinja2
      python27Packages.ldap
      python27Packages.lxml
      python27Packages.mock
      python27Packages.passlib
      #      python27Packages.pillow
      python27Packages.psutil
      python27Packages.psycopg2
      python27Packages.pyPdf
      python27Packages.pychart
      python27Packages.pydot
      python27Packages.pyparsing1
      python27Packages.pyserial
      python27Packages.pyusb
      python27Packages.pyyaml
      python27Packages.qrcode
      python27Packages.requests2
      python27Packages.simplejson
      python27Packages.six
      python27Packages.unittest2
      python27Packages.vobject
      python27Packages.werkzeug

      (with pkgs; buildPythonPackage rec {
        name = "Pillow-2.9.0";
    
        src = pkgs.fetchurl {
          url = "http://pypi.python.org/packages/source/P/Pillow/${name}.zip";
          sha256 = "1mal92cwh85z6zqx7lrmg0dbqb2gw2cbb2fm6xh0fivmszz8vnyi";
        };
    
        # Check is disabled because of assertion errors, see
        # https://github.com/python-pillow/Pillow/issues/1259
        doCheck = false;
    
        buildInputs = with self; [
          pkgs.freetype
    	  pkgs.libjpeg
    	  pkgs.zlib
    	  pkgs.libtiff
    	  pkgs.libwebp
    	  pkgs.tcl
    	  python27Packages.nose
    	  pkgs.lcms2
    	];
    
        # NOTE: we use LCMS_ROOT as WEBP root since there is not other setting for webp.
        preConfigure = ''
          sed -i "setup.py" \
              -e 's|^FREETYPE_ROOT =.*$|FREETYPE_ROOT = _lib_include("${pkgs.freetype}")|g ;
                  s|^JPEG_ROOT =.*$|JPEG_ROOT = _lib_include("${pkgs.libjpeg}")|g ;
                  s|^ZLIB_ROOT =.*$|ZLIB_ROOT = _lib_include("${pkgs.zlib}")|g ;
                  s|^LCMS_ROOT =.*$|LCMS_ROOT = _lib_include("${pkgs.libwebp}")|g ;
                  s|^TIFF_ROOT =.*$|TIFF_ROOT = _lib_include("${pkgs.libtiff}")|g ;
                  s|^TCL_ROOT=.*$|TCL_ROOT = _lib_include("${pkgs.tcl}")|g ;'
        ''
        # Remove impurities
        + stdenv.lib.optionalString stdenv.isDarwin ''
          substituteInPlace setup.py \
            --replace '"/Library/Frameworks",' "" \
            --replace '"/System/Library/Frameworks"' ""
        '';
    
        meta = {
          homepage = "https://python-pillow.github.io/";
    
          description = "Fork of The Python Imaging Library (PIL)";
    
          longDescription = ''
            The Python Imaging Library (PIL) adds image processing
            capabilities to your Python interpreter.  This library
            supports many file formats, and provides powerful image
            processing and graphics capabilities.
          '';
    
          license = "http://www.pythonware.com/products/pil/license.htm";
    
          maintainers = with maintainers; [ goibhniu prikhi ];
        };
      })
    ];    
  };
}