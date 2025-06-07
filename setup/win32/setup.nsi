# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO: Avoid to uninstall the database
# TODO: We can update the server or the clients without to uninstall the all-in-one
# TODO: Add startmenu handling (link to localhost + uninstall)

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
    !define MAJOR_VERSION '15'
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

!define PRODUCT_NAME "Odoo"
!define DISPLAY_NAME "${PRODUCT_NAME} ${MAJOR_VERSION}.${MINOR_VERSION}"

!define UNINSTALL_BASE_REGISTRY_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall"
!define UNINSTALL_REGISTRY_KEY "${UNINSTALL_BASE_REGISTRY_KEY}\${DISPLAY_NAME}"

!define UNINSTALL_REGISTRY_KEY_SERVER "${UNINSTALL_BASE_REGISTRY_KEY}\Odoo Server ${VERSION}"

!define REGISTRY_KEY "SOFTWARE\${DISPLAY_NAME}"

!define DEFAULT_POSTGRESQL_HOSTNAME 'localhost'
!define DEFAULT_POSTGRESQL_PORT 5432
!define DEFAULT_POSTGRESQL_USERNAME 'openpg'
!define DEFAULT_POSTGRESQL_PASSWORD 'openpgpwd'

Name '${DISPLAY_NAME}'
Caption "${PRODUCT_NAME} ${VERSION} Setup"
OutFile "${TOOLSDIR}\server\odoo_setup_${VERSION}.exe"
SetCompressor /SOLID /FINAL lzma
ShowInstDetails hide

BrandingText '${PRODUCT_NAME} ${VERSION}'

RequestExecutionLevel admin

!insertmacro GetParameters
!insertmacro GetOptions

Var Option_AllInOne
Var HasPostgreSQL
Var cmdLineParams

Var TextPostgreSQLHostname
Var TextPostgreSQLPort
Var TextPostgreSQLUsername
Var TextPostgreSQLPassword

Var HWNDPostgreSQLHostname
Var HWNDPostgreSQLPort
Var HWNDPostgreSQLUsername
Var HWNDPostgreSQLPassword

Var ProxyTokenDialog
Var ProxyTokenLabel
Var ProxyTokenText
Var ProxyTokenPwd

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
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE ComponentLeave
!insertmacro MUI_PAGE_COMPONENTS
Page Custom ShowPostgreSQL LeavePostgreSQL
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE dir_leave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
Page Custom ShowProxyTokenDialogPage
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
LangString DESC_Odoo_Server ${LANG_ENGLISH} "Install the Odoo Server with all the Odoo standard modules."
LangString DESC_PostgreSQL ${LANG_ENGLISH} "Install the PostgreSQL RDBMS used by Odoo."
LangString DESC_FinishPage_Link ${LANG_ENGLISH} "Contact Odoo for Partnership and/or Support"
LangString DESC_AtLeastOneComponent ${LANG_ENGLISH} "You have to choose at least one component"
LangString DESC_CanNotInstallPostgreSQL ${LANG_ENGLISH} "You can not install the PostgreSQL database without the Odoo Server"
LangString WARNING_HostNameIsEmpty ${LANG_ENGLISH} "The hostname for the connection to the PostgreSQL Server is empty"
LangString WARNING_UserNameIsEmpty ${LANG_ENGLISH} "The username for the connection to the PostgreSQL Server is empty"
LangString WARNING_PasswordIsEmpty ${LANG_ENGLISH} "The password for the connection to the PostgreSQL Server is empty"
LangString WARNING_PortIsWrong ${LANG_ENGLISH} "The port for the connexion to the PostgreSQL Server is wrong (default: 5432)"
LangString DESC_PostgreSQLPage ${LANG_ENGLISH} "Configure the information for the PostgreSQL connection"
LangString DESC_PostgreSQL_Hostname ${LANG_ENGLISH} "Hostname"
LangString DESC_PostgreSQL_Port ${LANG_ENGLISH} "Port"
LangString DESC_PostgreSQL_Username ${LANG_ENGLISH} "Username"
LangString DESC_PostgreSQL_Password ${LANG_ENGLISH} "Password"
LangString Profile_AllInOne ${LANG_ENGLISH} "Odoo Server And PostgreSQL Server"
LangString Profile_Server ${LANG_ENGLISH} "Odoo Server Only"
LangString Profile_IOT ${LANG_ENGLISH} "Odoo IoT"
LangString TITLE_Odoo_Server ${LANG_ENGLISH} "Odoo Server"
LangString TITLE_PostgreSQL ${LANG_ENGLISH} "PostgreSQL Database"
LangString TITLE_IOT ${LANG_ENGLISH} "Odoo IoT"
LangString TITLE_Nginx ${LANG_ENGLISH} "Nginx WebServer"
LangString TITLE_Ghostscript ${LANG_ENGLISH} "Ghostscript interpreter"
LangString DESC_FinishPageText ${LANG_ENGLISH} "Start Odoo"
LangString UnsafeDirText ${LANG_ENGLISH} "Installing outside of $PROGRAMFILES64 is not recommended.$\nDo you want to continue ?"

; French
LangString DESC_Odoo_Server ${LANG_FRENCH} "Installation du Serveur Odoo avec tous les modules Odoo standards."
LangString DESC_PostgreSQL ${LANG_FRENCH} "Installation de la base de données PostgreSQL utilisée par Odoo."
LangString DESC_FinishPage_Link ${LANG_FRENCH} "Contactez Odoo pour un Partenariat et/ou du Support"
LangString DESC_AtLeastOneComponent ${LANG_FRENCH} "Vous devez choisir au moins un composant"
LangString DESC_CanNotInstallPostgreSQL ${LANG_FRENCH} "Vous ne pouvez pas installer la base de données PostgreSQL sans le serveur Odoo"
LangString WARNING_HostNameIsEmpty ${LANG_FRENCH} "L'adresse pour la connection au serveur PostgreSQL est vide"
LangString WARNING_UserNameIsEmpty ${LANG_FRENCH} "Le nom d'utilisateur pour la connection au serveur PostgreSQL est vide"
LangString WARNING_PasswordIsEmpty ${LANG_FRENCH} "Le mot de passe pour la connection au serveur PostgreSQL est vide"
LangString WARNING_PortIsWrong ${LANG_FRENCH} "Le port pour la connection au serveur PostgreSQL est erroné (défaut: 5432)"
LangString DESC_PostgreSQLPage ${LANG_FRENCH} "Configurez les informations de connection pour le serveur PostgreSQL"
LangString DESC_PostgreSQL_Hostname ${LANG_FRENCH} "Hôte"
LangString DESC_PostgreSQL_Port ${LANG_FRENCH} "Port"
LangString DESC_PostgreSQL_Username ${LANG_FRENCH} "Utilisateur"
LangString DESC_PostgreSQL_Password ${LANG_FRENCH} "Mot de passe"
LangString Profile_AllInOne ${LANG_FRENCH} "Serveur Odoo Et Serveur PostgreSQL"
LangString Profile_Server ${LANG_FRENCH} "Seulement Le Serveur Odoo"
LangString Profile_IOT ${LANG_FRENCH} "Odoo IoT"
LangString TITLE_Odoo_Server ${LANG_FRENCH} "Serveur Odoo"
LangString TITLE_PostgreSQL ${LANG_FRENCH} "Installation du serveur de base de données PostgreSQL"
LangString TITLE_IOT ${LANG_FRENCH} "Odoo IoT"
LangString TITLE_Nginx ${LANG_FRENCH} "Installation du serveur web Nginx"
LangString TITLE_Ghostscript ${LANG_FRENCH} "Installation de l'interpréteur Ghostscript"
LangString DESC_FinishPageText ${LANG_FRENCH} "Démarrer Odoo"
LangString UnsafeDirText ${LANG_FRENCH} "Installer en dehors de $PROGRAMFILES64 n'est pas recommandé.$\nVoulez-vous continuer ?"

InstType /NOCUSTOM
InstType $(Profile_AllInOne)
InstType $(Profile_Server)
InstType $(Profile_IOT)

Section $(TITLE_Odoo_Server) SectionOdoo_Server
    SectionIn 1 2 3

    # Installing winpython
    SetOutPath "$INSTDIR\python"
    File /r /x "__pycache__" "${TOOLSDIR}\WinPy64\python-${PYTHONVERSION}.amd64\*"

    SetOutPath "$INSTDIR\nssm"
    File /r /x "src" "${TOOLSDIR}\nssm-2.24\*"

    SetOutPath "$INSTDIR\server"
    File /r /x "wkhtmltopdf" /x "enterprise" "${TOOLSDIR}\server\*"

    SetOutPath "$INSTDIR\vcredist"
    File /r "${TOOLSDIR}\vcredist\*.exe"

    # Install Visual C redistribuable files
    DetailPrint "Installing Visual C++ redistributable files"
    nsExec::Exec '"$INSTDIR\vcredist\vc_redist.x64.exe" /q'

    SetOutPath "$INSTDIR\thirdparty"
    File /r "${TOOLSDIR}\wkhtmltopdf\*"

    # If there is a previous install of the Odoo Server, keep the login/password from the config file
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_host" $TextPostgreSQLHostname
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_user" $TextPostgreSQLUsername
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_password" $TextPostgreSQLPassword
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_port" $TextPostgreSQLPort
    # Fix the addons path
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "addons_path" "$INSTDIR\server\odoo\addons"
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "bin_path" "$INSTDIR\thirdparty"
    # Set data_dir
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "data_dir" "$INSTDIR\sessions"

    # if we're going to install postgresql force it's path,
    # otherwise we consider it's always done and/or correctly tune by users
    ${If} $HasPostgreSQL == 0
        WriteIniStr "$INSTDIR\server\odoo.conf" "options" "pg_path" "$INSTDIR\PostgreSQL\bin"
    ${EndIf}

    # Productivity Apps
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "default_productivity_apps" "True"
    DetailPrint "Installing Windows service"
    nsExec::ExecTOLog '"$INSTDIR\python\python.exe" "$INSTDIR\server\odoo-bin" --stop-after-init -c "$INSTDIR\server\odoo.conf" --logfile "$INSTDIR\server\odoo.log" -s'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" install ${SERVICENAME} "$INSTDIR\python\python.exe"'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} AppDirectory "$\"$INSTDIR\python$\""'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} AppParameters "\"$INSTDIR\server\odoo-bin\" -c "\"$INSTDIR\server\odoo.conf\"'
    nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} ObjectName "LOCALSERVICE"'
    AccessControl::GrantOnFile  "$INSTDIR" "LOCALSERVICE" "FullAccess"

    Call RestartOdooService
SectionEnd

Section $(TITLE_PostgreSQL) SectionPostgreSQL
    SectionIn 1
    SetOutPath '$TEMP'
    VAR /GLOBAL postgresql_exe_filename
    VAR /GLOBAL postgresql_url

    StrCpy $postgresql_exe_filename "postgresql-12.4-1-windows-x64.exe"

    StrCpy $postgresql_url "https://get.enterprisedb.com/postgresql/$postgresql_exe_filename"
    nsExec::Exec 'net user openpgsvc /delete'

    DetailPrint "Downloading PostgreSQl"
    NScurl::http get "$postgresql_url" "$TEMP/$postgresql_exe_filename" /PAGE /END
    pop $0

    ReadRegStr $0 HKLM "System\CurrentControlSet\Control\ComputerName\ActiveComputerName" "ComputerName"
    StrCmp $0 "" win9x
    Goto done
    win9x:
        ReadRegStr $0 HKLM "System\CurrentControlSet\Control\ComputerName\ComputerName" "ComputerName"
    done:
    Rmdir /r "$INSTDIR\PostgreSQL"
    DetailPrint "Installing PostgreSQL"
    ExecWait '"$TEMP\$postgresql_exe_filename" \
        --mode unattended \
        --prefix "$INSTDIR\PostgreSQL" \
        --datadir "$INSTDIR\PostgreSQL\data" \
        --servicename "PostgreSQL_For_Odoo" \
        --serviceaccount "openpgsvc" --servicepassword "0p3npgsvcPWD" \
        --superaccount "$TextPostgreSQLUsername" --superpassword "$TextPostgreSQLPassword" \
        --serverport $TextPostgreSQLPort'
SectionEnd

Section $(TITLE_IOT) IOT
    SectionIn 3
    DetailPrint "Configuring TITLE_IOT"
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "server_wide_modules" "web,hw_posbox_homepage,hw_drivers"
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "list_db" "False"
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "max_cron_threads" "0"
    nsExec::ExecToStack '"$INSTDIR\python\python.exe" "$INSTDIR\server\odoo-bin" genproxytoken'
    pop $0
    pop $ProxyTokenPwd
SectionEnd


Section $(TITLE_Nginx) Nginx
    SectionIn 3
    SetOutPath '$TEMP'
    VAR /GLOBAL nginx_zip_filename
    VAR /GLOBAL nginx_url

    # need unzip plugin:
    # https://nsis.sourceforge.io/mediawiki/images/5/5a/NSISunzU.zip
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
    File "..\..\odoo\addons\point_of_sale\tools\posbox\overwrite_after_init\etc\ssl\certs\nginx-cert.crt"
    File "..\..\odoo\addons\point_of_sale\tools\posbox\overwrite_after_init\etc\ssl\private\nginx-cert.key"
SectionEnd

Section $(TITLE_Ghostscript) SectionGhostscript
    SectionIn 3
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
    Call RestartOdooService
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
    !insertmacro MUI_DESCRIPTION_TEXT ${SectionOdoo_Server} $(DESC_Odoo_Server)
    !insertmacro MUI_DESCRIPTION_TEXT ${SectionPostgreSQL} $(DESC_PostgreSQL)
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
    StrCmp $1 "" nginx_dir_not_found
    Rmdir /R "$INSTDIR\$1"
    nginx_dir_not_found:
    FindClose $0
    DeleteRegKey HKLM "${UNINSTALL_REGISTRY_KEY}"
SectionEnd

Function .onInit
    VAR /GLOBAL previous_install_dir
    SetRegView 64
    ReadRegStr $previous_install_dir HKLM "${REGISTRY_KEY}" "Install_Dir"
    ${If} $previous_install_dir == ""
        StrCpy $INSTDIR "$PROGRAMFILES64\Odoo ${VERSION}"
        WriteRegStr HKLM "${REGISTRY_KEY}" "Install_dir" "$INSTDIR"
    ${Else}
        StrCpy $INSTDIR $previous_install_dir
    ${EndIf}

    Push $R0
    ${GetParameters} $cmdLineParams
    ClearErrors
    Pop $R0

    StrCpy $Option_AllInOne 0
    StrCpy $HasPostgreSQL 0

    StrCpy $TextPostgreSQLHostname ${DEFAULT_POSTGRESQL_HOSTNAME}
    StrCpy $TextPostgreSQLPort ${DEFAULT_POSTGRESQL_PORT}
    StrCpy $TextPostgreSQLUsername ${DEFAULT_POSTGRESQL_USERNAME}
    StrCpy $TextPostgreSQLPassword ${DEFAULT_POSTGRESQL_PASSWORD}

    Push $R0
    ${GetOptions} $cmdLineParams '/allinone' $R0
    IfErrors +2 0
    StrCpy $Option_AllInOne 1
    Pop $R0

    StrCmp $Option_AllInOne 1 AllInOneMode
    StrCmp $Option_AllInOne 0 NoAllInOneMode

    AllInOneMode:
        MessageBox MB_OK|MB_ICONINFORMATION "All In One"

    NoAllInOneMode:

    !insertmacro MUI_LANGDLL_DISPLAY

    ClearErrors
    EnumRegKey $0 HKLM "SOFTWARE\PostgreSQL\Installations" 0
    IfErrors DoInstallPostgreSQL 0
    StrCmp $0 "" DoInstallPostgreSQL
    StrCpy $HasPostgreSQL 1
    !insertmacro UnselectSection ${SectionPostgreSQL}
    SectionSetFlags ${SectionPostgreSQL} ${SF_RO}

    DoInstallPostgreSQL:
FunctionEnd

Function .onSelChange
    ${If} $HasPostgreSQL == 1
        !insertmacro UnselectSection ${SectionPostgreSQL}
    ${EndIf}
FunctionEnd

Function PostgreSQLOnBack
FunctionEnd

Function ShowPostgreSQL
    GetCurInstType $R0
    IntCmp $R0 1 bypassPostgresConfig
    Intcmp $R0 2 bypassPostgresConfig

    nsDialogs::Create /NOUNLOAD 1018
    Pop $0

    ${If} $0 == error
        Abort
    ${EndIf}

    GetFunctionAddress $0 PostgreSQLOnBack
    nsDialogs::OnBack $0

    ${NSD_CreateLabel} 0 0 100% 10u $(DESC_PostgreSQLPage)
    Pop $0

    ${NSD_CreateLabel} 0 45 60u 12u $(DESC_PostgreSQL_Hostname)
    Pop $0
    ${NSD_CreateText} 100 45 150u 12u $TextPostgreSQLHostname
    Pop $HWNDPostgreSQLHostname

    ${NSD_CreateLabel} 0 75 60u 12u $(DESC_PostgreSQL_Port)
    Pop $0
    ${NSD_CreateNumber} 100 75 150u 12u $TextPostgreSQLPort
    Pop $HWNDPostgreSQLPort
    ${NSD_CreateLabel} 0 105 60u 12u $(DESC_PostgreSQL_Username)
    Pop $0
    ${NSD_CreateText} 100 105 150u 12u $TextPostgreSQLUsername
    Pop $HWNDPostgreSQLUsername
    ${NSD_CreateLabel} 0 135 60u 12u $(DESC_PostgreSQL_Password)
    Pop $0
    ${NSD_CreateText} 100 135 150u 12u $TextPostgreSQLPassword
    Pop $HWNDPostgreSQLPassword

    nsDialogs::Show
    bypassPostgresConfig:
FunctionEnd

Function LeavePostgreSQL
    ${NSD_GetText} $HWNDPostgreSQLHostname $TextPostgreSQLHostname
    ${NSD_GetText} $HWNDPostgreSQLPort $TextPostgreSQLPort
    ${NSD_GetText} $HWNDPostgreSQLUsername $TextPostgreSQLUsername
    ${NSD_GetText} $HWNDPostgreSQLPassword $TextPostgreSQLPassword
    StrLen $1 $TextPostgreSQLHostname
    ${If} $1 == 0
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_HostNameIsEmpty)
        Abort
    ${EndIf}

    ${If} $TextPostgreSQLPort <= 0
    ${OrIf} $TextPostgreSQLPort > 65535
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_PortIsWrong)
        Abort
    ${EndIf}

    StrLen $1 $TextPostgreSQLUsername
    ${If} $1 == 0
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_UserNameIsEmpty)
        Abort
    ${EndIf}

    StrLen $1 $TextPostgreSQLPassword
    ${If} $1 == 0
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_PasswordIsEmpty)
        Abort
    ${EndIf}
FunctionEnd

Function ShowProxyTokenDialogPage
    GetCurInstType $R0
    IntCmp $R0 2 doProxyToken bypassProxyToken
    doProxyToken:
        nsDialogs::Create 1018
        Pop $ProxyTokenDialog
        ${IF} $ProxyTokenDialog == !error
            Abort
        ${EndIf}

        ${NSD_CreateLabel} 0 0 100% 25% "Here is your access token for the Odoo IOT, please write it down in a safe place, you will need it to configure the IOT"
        Pop $ProxyTokenLabel

        ${NSD_CreateText} 0 30% 100% 13u $ProxyTokenPwd
        Pop $ProxyTokenText
        ${NSD_Edit_SetreadOnly} $ProxyTokenText 1
        ${NSD_AddStyle}  $ProxyTokenText ${SS_CENTER}
        nsDialogs::Show
    bypassProxyToken:
FunctionEnd

Function ComponentLeave
    SectionGetFlags ${SectionOdoo_Server} $0
    IntOp $0 $0 & ${SF_SELECTED}
    IntCmp $0 ${SF_SELECTED} Done

    SectionGetFlags ${SectionPostgreSQL} $0
    IntOp $0 $0 & ${SF_SELECTED}
    IntCmp $0 ${SF_SELECTED} DontInstallPostgreSQL

    DontInstallPostgreSQL:
        MessageBox MB_ICONEXCLAMATION|MB_OK $(DESC_CanNotInstallPostgreSQL)
        Abort
    Done:
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
