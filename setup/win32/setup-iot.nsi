# Part of Odoo. See LICENSE file for full copyright and licensing details.
Unicode True

!include 'MUI2.nsh'
!include 'FileFunc.nsh'
!include 'LogicLib.nsh'
!include 'Sections.nsh'
!include 'x64.nsh'

!macro IfKeyExists ROOT MAIN_KEY KEY
    # This macro comes from http://nsis.sourceforge.net/Check_for_a_Registry_Key
    Push $R0
    Push $R1
    Push $R2

    # XXX bug if ${ROOT}, ${MAIN_KEY} or ${KEY} use $R0 or $R1

    StrCpy $R1 "0" # loop index
    StrCpy $R2 "0" # not found

    ${Do}
        EnumRegKey $R0 ${ROOT} "${MAIN_KEY}" "$R1"
        ${If} $R0 == "${KEY}"
            StrCpy $R2 "1" # found
            ${Break}
        ${EndIf}
        IntOp $R1 $R1 + 1
    ${LoopWhile} $R0 != ""

    ClearErrors

    Exch 2
    Pop $R0
    Pop $R1
    Exch $R2
!macroend

!define PUBLISHER 'Odoo S.A.'

!ifndef MAJOR_VERSION
    !define MAJOR_VERSION '16'
!endif

!ifndef MINOR_VERSION
    !define MINOR_VERSION '0'
!endif

!ifndef REVISION_VERSION
    !define REVISION_VERSION 'alpha1'
!endif

!ifndef VERSION
    !define VERSION "${MAJOR_VERSION}.${MINOR_VERSION}"
!endif

!ifndef PYTHONVERSION
	!define PYTHONVERSION '3.10.11'
!endif

!ifndef SERVICENAME
	!define SERVICENAME 'odoo-server-${VERSION}'
!endif

!ifndef TOOLSDIR
	!define TOOLSDIR 'c:\odoobuild'
!endif

!define PRODUCT_NAME "Odoo IOT"
!define DISPLAY_NAME "${PRODUCT_NAME} ${MAJOR_VERSION}.${MINOR_VERSION}"

!define UNINSTALL_BASE_REGISTRY_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall"
!define UNINSTALL_REGISTRY_KEY "${UNINSTALL_BASE_REGISTRY_KEY}\${DISPLAY_NAME}"

!define UNINSTALL_REGISTRY_KEY_SERVER "${UNINSTALL_BASE_REGISTRY_KEY}\Odoo Server ${VERSION}"

!define REGISTRY_KEY "SOFTWARE\${DISPLAY_NAME}"

Name '${DISPLAY_NAME}'
Caption "${PRODUCT_NAME} ${VERSION} Setup"
OutFile "${TOOLSDIR}\server\odoo_iot_setup_${VERSION}.exe"
SetCompressor /SOLID /FINAL lzma
ShowInstDetails hide

BrandingText '${PRODUCT_NAME} ${VERSION}'

RequestExecutionLevel admin

!insertmacro GetParameters
!insertmacro GetOptions

Var /GLOBAL cmdLineParams

!define STATIC_PATH "static"
!define PIXMAPS_PATH "${STATIC_PATH}\pixmaps"

!define MUI_ABORTWARNING
!define MUI_ICON "${PIXMAPS_PATH}\odoo-icon.ico"

!define MUI_WELCOMEFINISHPAGE_BITMAP "${PIXMAPS_PATH}\odoo-intro.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${PIXMAPS_PATH}\odoo-intro.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${PIXMAPS_PATH}\odoo-slogan.bmp"
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH
!define MUI_HEADER_TRANSPARENT_TEXT ""

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${STATIC_PATH}\doc\LICENSE"
!define MUI_COMPONENTSPAGE_SMALLDESC
!insertmacro MUI_PAGE_COMPONENTS
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE dir_leave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_CHECKED
!define MUI_FINISHPAGE_RUN_TEXT "$(DESC_FinishPageText)"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
!define MUI_FINISHPAGE_LINK $(DESC_FinishPage_Link)
!define MUI_FINISHPAGE_LINK_LOCATION "https://www.odoo.com/page/contactus"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_RESERVEFILE_LANGDLL

; English
LangString DESC_Odoo_IOT ${LANG_ENGLISH} "Install the Odoo Server with IOT modules."
LangString DESC_FinishPage_Link ${LANG_ENGLISH} "Contact Odoo for Partnership and/or Support"
LangString TITLE_Odoo_IOT ${LANG_ENGLISH} "Odoo IoT"
LangString TITLE_Nginx ${LANG_ENGLISH} "Nginx WebServer"
LangString TITLE_Ghostscript ${LANG_ENGLISH} "Ghostscript interpreter"
LangString DESC_FinishPageText ${LANG_ENGLISH} "Start Odoo"
LangString UnsafeDirText ${LANG_ENGLISH} "Installing outside of $PROGRAMFILES64 is not recommended.$\nDo you want to continue ?"

; French
LangString DESC_Odoo_IOT ${LANG_FRENCH} "Installation du Serveur Odoo avec les modules IOT."
LangString DESC_FinishPage_Link ${LANG_FRENCH} "Contactez Odoo pour un Partenariat et/ou du Support"
LangString TITLE_Odoo_IOT ${LANG_FRENCH} "Odoo IoT"
LangString TITLE_Nginx ${LANG_FRENCH} "Installation du serveur web Nginx"
LangString TITLE_Ghostscript ${LANG_FRENCH} "Installation de l'interpréteur Ghostscript"
LangString DESC_FinishPageText ${LANG_FRENCH} "Démarrer Odoo"
LangString UnsafeDirText ${LANG_FRENCH} "Installer en dehors de $PROGRAMFILES64 n'est pas recommandé.$\nVoulez-vous continuer ?"

InstType /NOCUSTOM

Section $(TITLE_Odoo_IOT) SectionOdoo_IOT

    # Installing winpython
    SetOutPath "$INSTDIR\python"
    File /r /x "__pycache__" "${TOOLSDIR}\WinPy64\python-${PYTHONVERSION}.amd64\*"

    SetOutPath "$INSTDIR\nssm"
    File /r /x "src" "${TOOLSDIR}\nssm-2.24\*"

    # installing git
    VAR /GLOBAL git_zip_filename
    VAR /GLOBAL git_zip_url
    StrCpy $git_zip_filename "MinGit-2.47.1-64-bit.zip"
    StrCpy $git_zip_url "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/$git_zip_filename"

    DetailPrint "Downloading git"
    NScurl::http get "$git_zip_url" "$TEMP\$git_zip_filename" /PAGE /END
    DetailPrint "Unzipping git"
    nsisunz::UnzipToLog "$TEMP\$git_zip_filename" "$INSTDIR\git"

    # cloning odoo
    SetOutPath "$INSTDIR"
    DetailPrint "Cloning Odoo"
    nsExec::Exec '"$INSTDIR\git\cmd\git.exe" clone --filter tree:0 -b 18.0 --single-branch https://github.com/odoo/odoo.git "$INSTDIR\server"'
    pop $0

    DetailPrint "Installing vcredist"
    SetOutPath "$INSTDIR\vcredist"
    File /r "${TOOLSDIR}\vcredist\*.exe"

    # Install Visual C redistribuable files
    DetailPrint "Installing Visual C++ redistributable files"
    nsExec::Exec '"$INSTDIR\vcredist\vc_redist.x64.exe" /q'

    DetailPrint "Writing odoo.conf"
    # Fix the addons path
    WriteIniStr "$INSTDIR\odoo.conf" "options" "addons_path" "$INSTDIR\server\odoo\addons,$INSTDIR\server\addons"
    # Set data_dir
    WriteIniStr "$INSTDIR\odoo.conf" "options" "data_dir" "$INSTDIR\sessions"

    DetailPrint "Configuring $(TITLE_Odoo_IOT)"
    nsExec::ExecTOLog '"$INSTDIR\python\python.exe" "$INSTDIR\server\odoo-bin" --stop-after-init -c "$INSTDIR\odoo.conf" --logfile "$INSTDIR\odoo.log" -s'
    WriteIniStr "$INSTDIR\odoo.conf" "options" "server_wide_modules" "web,hw_posbox_homepage,hw_drivers"
    WriteIniStr "$INSTDIR\odoo.conf" "options" "list_db" "False"
    WriteIniStr "$INSTDIR\odoo.conf" "options" "max_cron_threads" "0"

    DetailPrint "Installing Windows service"
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" install ${SERVICENAME} "$INSTDIR\python\python.exe"'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} AppDirectory "$\"$INSTDIR\python$\""'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} AppParameters "\"$INSTDIR\server\odoo-bin\" -c "\"$INSTDIR\odoo.conf\"'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} ObjectName "LOCALSERVICE"'
    AccessControl::GrantOnFile  "$INSTDIR" "LOCALSERVICE" "FullAccess"

    Call RestartOdooService
SectionEnd

Section -$(TITLE_Nginx) Nginx
    SetOutPath '$TEMP'
    VAR /GLOBAL nginx_zip_filename
    VAR /GLOBAL nginx_url

    StrCpy $nginx_zip_filename "nginx-1.22.0.zip"
    StrCpy $nginx_url "https://nginx.org/download/$nginx_zip_filename"

    DetailPrint "Downloading Nginx"
    NScurl::http get "$nginx_url" "$TEMP\$nginx_zip_filename" /PAGE /END
    DetailPrint "Temp dir: $TEMP\$nginx_zip_filename"
    DetailPrint "Unzip Nginx"
    nsisunz::UnzipToLog "$TEMP\$nginx_zip_filename" "$INSTDIR"

    Pop $0
    StrCmp $0 "success" ok
      DetailPrint "$0" ;print error message to log
    ok:

    FindFirst $0 $1 "$INSTDIR\nginx*"
    DetailPrint "Setting up nginx"
    SetOutPath "$INSTDIR\$1\conf"
    CreateDirectory $INSTDIR\$1\temp
    CreateDirectory $INSTDIR\$1\logs
    FindClose $0
    File "conf\nginx\nginx.conf"
    # Temporary certs for the first start
    File "..\..\odoo\addons\iot_box_image\overwrite_after_init\etc\ssl\certs\nginx-cert.crt"
    File "..\..\odoo\addons\iot_box_image\overwrite_after_init\etc\ssl\private\nginx-cert.key"
SectionEnd

Section -$(TITLE_Ghostscript) SectionGhostscript
    SetOutPath '$TEMP'
    VAR /GLOBAL ghostscript_exe_filename
    VAR /GLOBAL ghostscript_url

    StrCpy $ghostscript_exe_filename "gs10012w64.exe"
    StrCpy $ghostscript_url "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10012/$ghostscript_exe_filename"

    DetailPrint "Downloading Ghostscript"
    NScurl::http get "$ghostscript_url" "$TEMP\$ghostscript_exe_filename" /PAGE /END
    DetailPrint "Temp dir: $TEMP\$ghostscript_exe_filename"

    Rmdir /r "INSTDIR\Ghostscript"
    DetailPrint "Installing Ghostscript"
    ExecWait '"$TEMP\$ghostscript_exe_filename" \
        /S \
        /D=$INSTDIR\Ghostscript'
SectionEnd

Section -Post
    WriteRegExpandStr HKLM "${UNINSTALL_REGISTRY_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegExpandStr HKLM "${UNINSTALL_REGISTRY_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "DisplayName" "${DISPLAY_NAME}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion" "${MAJOR_VERSION}.${MINOR_VERSION}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "HelpLink" "support@odoo.com"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "HelpTelephone" "+32.81.81.37.00"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "URLInfoAbout" "https://www.odoo.com"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "Contact" "sales@odoo.com"
    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "NoModify" "1"
    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "NoRepair" "1"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SectionOdoo_IOT} $(DESC_Odoo_IOT)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
    # Check if the server is installed
    !insertmacro IfKeyExists "HKLM" "${UNINSTALL_REGISTRY_KEY_SERVER}" "UninstallString"
    Pop $R0
    ReadRegStr $0 HKLM "${UNINSTALL_REGISTRY_KEY_SERVER}" "UninstallString"
    ExecWait '"$0" /S'
    ExecWait '"$INSTDIR\Ghostscript\uninstgs.exe" /S'

    nsExec::Exec "net stop ${SERVICENAME}"
    nsExec::Exec "sc delete ${SERVICENAME}"
    sleep 2

    Rmdir /r "$INSTDIR\server"
    Rmdir /r "$INSTDIR\sessions"
    Rmdir /r "$INSTDIR\thirdparty"
    Rmdir /r "$INSTDIR\python"
    Rmdir /r "$INSTDIR\nssm"
    FindFirst $0 $1 "$INSTDIR\nginx*"
    Rmdir /R "$INSTDIR\$1"
    FindClose $0
    DeleteRegKey HKLM "${UNINSTALL_REGISTRY_KEY}"
SectionEnd

Function .onInit
    VAR /GLOBAL previous_install_dir
    SetRegView 64
    ReadRegStr $previous_install_dir HKLM "${REGISTRY_KEY}" "Install_Dir"
    ${If} $previous_install_dir == ""
        StrCpy $INSTDIR "$PROGRAMFILES64\Odoo IOT ${VERSION}"
        WriteRegStr HKLM "${REGISTRY_KEY}" "Install_dir" "$INSTDIR"
    ${Else}
        StrCpy $INSTDIR $previous_install_dir
    ${EndIf}

    Push $R0
    ${GetParameters} $cmdLineParams
    ClearErrors
    Pop $R0

    !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

Function LaunchLink
    ExecShell "open" "http://localhost:8069/"
FunctionEnd

Function RestartOdooService
    DetailPrint "Restarting Odoo Service"
    ExecWait "net stop ${SERVICENAME}"
    ExecWait "net start ${SERVICENAME}"
FunctionEnd

Function dir_leave
    StrLen $0 $PROGRAMFILES64
    StrCpy $0 $INSTDIR $0
    StrCmp $0 $PROGRAMFILES64 continue
    MessageBox MB_YESNO|MB_ICONEXCLAMATION "$(UnsafeDirText)" IDYES continue IDNO aborting
    aborting:
        Abort
    continue:
FunctionEnd
