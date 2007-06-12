;NSIS Modern User Interface
;Start Menu Folder Selection Example Script
;Written by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI.nsh"

;--------------------------------
;General

  ;Name and file
  Name "TinyERP Server"
  OutFile "tinyerp-server-setup.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\TinyERP Server"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\TinyERP Server" ""

  ;Vista redirects $SMPROGRAMS to all users without this
  RequestExecutionLevel admin

;--------------------------------
;Variables

  Var MUI_TEMP
  Var STARTMENU_FOLDER

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !define MUI_ICON ".\pixmaps\tinyerp.ico"
  !define MUI_UNICON ".\pixmaps\tinyerp.ico"
  !define MUI_WELCOMEFINISHPAGE_BITMAP ".\pixmaps\tinyerp-intro.bmp"
  !define MUI_HEADERIMAGE
  !define MUI_HEADERIMAGE_BITMAP ".\pixmaps\tinyerp-header.bmp"

  !insertmacro MUI_PAGE_WELCOME
  !insertmacro MUI_PAGE_LICENSE "doc\\License.rtf"
 # !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  
  ;Start Menu Folder Page Configuration
  !define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU" 
  !define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\TinyERP Server"
  !define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "TinyERP Server"
  
  !insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER
  
  !insertmacro MUI_PAGE_INSTFILES

  !define MUI_FINISHPAGE_NOAUTOCLOSE
  !define MUI_FINISHPAGE_RUN
  !define MUI_FINISHPAGE_RUN_CHECKED
  !define MUI_FINISHPAGE_RUN_TEXT "Start TinyERP Server"
  !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
  !define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
  !define MUI_FINISHPAGE_SHOWREADME $INSTDIR\README.txt
  !insertmacro MUI_PAGE_FINISH

  
  !insertmacro MUI_UNPAGE_WELCOME
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "TinyERP Server" SecTinyERPServer

  nsExec::Exec "net stop tinyerp-service"
  sleep 2

  SetOutPath "$INSTDIR"
  
  ;ADD YOUR OWN FILES HERE...
  File /r "dist\\*"

  SetOutPath "$INSTDIR\service"
  File /r "win32\\dist\\*"
  File "win32\\start.bat"
  File "win32\\stop.bat"

  ;Store installation folder
  WriteRegStr HKCU "Software\TinyERP Server" "" $INSTDIR
  
  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\TinyERP Server.lnk" "$INSTDIR\tinyerp-server.exe"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Start service.lnk" "$INSTDIR\service\start.bat"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Stop service.lnk" "$INSTDIR\service\stop.bat"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Edit config.lnk" "notepad.exe" "$INSTDIR\tinyerp-server.conf"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\View log.lnk" "notepad.exe" "$INSTDIR\tinyerp-server.log"
  
  !insertmacro MUI_STARTMENU_WRITE_END

  nsExec::Exec '"$INSTDIR\\tinyerp-server.exe" --stop-after-init --logfile "$INSTDIR\\tinyerp-server.log" -s'
  nsExec::Exec '"$INSTDIR\\service\\TinyERPServerService.exe" -auto -install'

SectionEnd

;Descriptions

  ;Language strings
  LangString DESC_SecTinyERPServer ${LANG_ENGLISH} "TinyERP Server."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecTinyERPServer} $(DESC_SecTinyERPServer)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END
 
;--------------------------------
;Uninstaller Section

Section "Uninstall"

  nsExec::Exec "net stop tinyerp-service"
  sleep 2
  nsExec::Exec '"$INSTDIR\\service\\TinyERPServerService.exe" -remove'
  sleep 2

  ;ADD YOUR OWN FILES HERE...
  Delete "$INSTDIR\Uninstall.exe"
  Push "$INSTDIR\addons"
  Push ""
  Call un.RmFilesButOne
  Delete "$INSTDIR\service\*"
  Delete "$INSTDIR\*"
  Delete "$INSTDIR\Uninstall.exe"

  Push "$INSTDIR\addons"
  Push ""
  Call un.RmDirsButOne
  RMDir "$INSTDIR\addons"
  RMDir "$INSTDIR\service"
  RMDir "$INSTDIR"
  
  !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP
    
  Delete "$SMPROGRAMS\$MUI_TEMP\TinyERP Server.lnk"
  Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"
  Delete "$SMPROGRAMS\$MUI_TEMP\Start service.lnk"
  Delete "$SMPROGRAMS\$MUI_TEMP\Stop service.lnk"
  
  ;Delete empty start menu parent diretories
  StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"
 
  startMenuDeleteLoop:
	ClearErrors
    RMDir $MUI_TEMP
    GetFullPathName $MUI_TEMP "$MUI_TEMP\.."
    
    IfErrors startMenuDeleteLoopDone
  
    StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop
  startMenuDeleteLoopDone:

  DeleteRegKey /ifempty HKCU "Software\TinyERP Server"

SectionEnd

Function LaunchLink
  nsExec::Exec "net start tinyerp-service"
FunctionEnd

Function un.RmDirsButOne
 Exch $R0 ; exclude dir
 Exch
 Exch $R1 ; route dir
 Push $R2
 Push $R3
 
  FindFirst $R3 $R2 "$R1\*.*"
  IfErrors Exit
 
  Top:
   StrCmp $R2 "." Next
   StrCmp $R2 ".." Next
   StrCmp $R2 $R0 Next
   IfFileExists "$R1\$R2\*.*" 0 Next
    RmDir /r "$R1\$R2"
 
   #Goto Exit ;uncomment this to stop it being recursive
 
   Next:
    ClearErrors
    FindNext $R3 $R2
    IfErrors Exit
   Goto Top
 
  Exit:
  FindClose $R3
 
 Pop $R3
 Pop $R2
 Pop $R1
 Pop $R0
FunctionEnd

Function un.RmFilesButOne
 Exch $R0 ; exclude file
 Exch
 Exch $R1 ; route dir
 Push $R2
 Push $R3
 
  FindFirst $R3 $R2 "$R1\*.*"
  IfErrors Exit
 
  Top:
   StrCmp $R2 "." Next
   StrCmp $R2 ".." Next
   StrCmp $R2 $R0 Next
   IfFileExists "$R1\$R2\*.*" Next
    Delete "$R1\$R2"
 
   #Goto Exit ;uncomment this to stop it being recursive
 
   Next:
    ClearErrors
    FindNext $R3 $R2
    IfErrors Exit
   Goto Top
 
  Exit:
  FindClose $R3
 
 Pop $R3
 Pop $R2
 Pop $R1
 Pop $R0
FunctionEnd
