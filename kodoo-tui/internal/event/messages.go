package event

type PromptField struct {
	Key         string
	Label       string
	Placeholder string
	Secret      bool
}

// RequestMakeTargetMsg asks the root app to confirm and run a Make target.
type RequestMakeTargetMsg struct {
	Target            string
	Vars              map[string]string
	Description       string
	RelevantKeys      []string
	PromptFields      []PromptField
	Interactive       bool
	RequireTypedCheck bool
	ConfirmWord       string
	SelectDatabase    bool
	DatabaseBackend   string
}

// RequestOpenEditorMsg asks the root app to open a file in $EDITOR.
type RequestOpenEditorMsg struct {
	Path string
}

// RequestUpdateConfigMsg asks the root app to update a configuration key.
type RequestUpdateConfigMsg struct {
	Key   string
	Value string
}

// EditorDoneMsg reports the result of an editor session.
type EditorDoneMsg struct {
	Path string
	Err  error
}
