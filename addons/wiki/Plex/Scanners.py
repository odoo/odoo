#=======================================================================
#
#   Python Lexical Analyser
#
#
#   Scanning an input stream
#
#=======================================================================

import Errors
from Regexps import BOL, EOL, EOF

class Scanner:
  """
  A Scanner is used to read tokens from a stream of characters
  using the token set specified by a Plex.Lexicon.

  Constructor:

    Scanner(lexicon, stream, name = '')

      See the docstring of the __init__ method for details.

  Methods:

    See the docstrings of the individual methods for more
    information.

    read() --> (value, text)
      Reads the next lexical token from the stream.

    position() --> (name, line, col)
      Returns the position of the last token read using the
      read() method.
    
    begin(state_name)
      Causes scanner to change state.
    
    produce(value [, text])
      Causes return of a token value to the caller of the
      Scanner.

  """

  lexicon = None        # Lexicon
  stream = None         # file-like object
  name = ''
  buffer = ''
  buf_start_pos = 0     # position in input of start of buffer
  next_pos = 0          # position in input of next char to read
  cur_pos = 0           # position in input of current char
  cur_line = 1          # line number of current char
  cur_line_start = 0    # position in input of start of current line
  start_pos = 0         # position in input of start of token
  start_line = 0        # line number of start of token
  start_col = 0         # position in line of start of token
  text = None           # text of last token read
  initial_state = None  # Node
  state_name = ''       # Name of initial state
  queue = None          # list of tokens to be returned
  trace = 0

  def __init__(self, lexicon, stream, name = ''):
    """
    Scanner(lexicon, stream, name = '')

      |lexicon| is a Plex.Lexicon instance specifying the lexical tokens
      to be recognised.

      |stream| can be a file object or anything which implements a
      compatible read() method.

      |name| is optional, and may be the name of the file being
      scanned or any other identifying string.
    """
    self.lexicon = lexicon
    self.stream = stream
    self.name = name
    self.queue = []
    self.initial_state = None
    self.begin('')
    self.next_pos = 0
    self.cur_pos = 0
    self.cur_line_start = 0
    self.cur_char = BOL
    self.input_state = 1

  def read(self):
    """
    Read the next lexical token from the stream and return a
    tuple (value, text), where |value| is the value associated with
    the token as specified by the Lexicon, and |text| is the actual
    string read from the stream. Returns (None, '') on end of file.
    """
    queue = self.queue
    while not queue:
      self.text, action = self.scan_a_token()
      if action is None:
        self.produce(None)
        self.eof()
      else:
        value = action.perform(self, self.text)
        if value is not None:
          self.produce(value)
    result = queue[0]
    del queue[0]
    return result

  def scan_a_token(self):
    """
    Read the next input sequence recognised by the machine
    and return (text, action). Returns ('', None) on end of
    file.
    """
    self.start_pos = self.cur_pos
    self.start_line = self.cur_line
    self.start_col = self.cur_pos - self.cur_line_start
#		if self.trace:
#			action = self.run_machine()
#		else:
#			action = self.run_machine_inlined()
    action = self.run_machine_inlined()
    if action:
      if self.trace:
        print "Scanner: read: Performing", action, "%d:%d" % (
          self.start_pos, self.cur_pos)
      base = self.buf_start_pos
      text = self.buffer[self.start_pos - base : self.cur_pos - base]
      return (text, action)
    else:
      if self.cur_pos == self.start_pos:
        if self.cur_char == EOL:
          self.next_char()
        if not self.cur_char or self.cur_char == EOF:
          return ('', None)
      raise Errors.UnrecognizedInput(self, self.state_name)
  
  def run_machine(self):
    """
    Run the machine until no more transitions are possible.
    """
    self.state = self.initial_state
    self.backup_state = None
    while self.transition():
      pass
    return self.back_up()
  
  def run_machine_inlined(self):
    """
    Inlined version of run_machine for speed.
    """
    state = self.initial_state
    cur_pos = self.cur_pos
    cur_line = self.cur_line
    cur_line_start = self.cur_line_start
    cur_char = self.cur_char
    input_state = self.input_state
    next_pos = self.next_pos
    buffer = self.buffer
    buf_start_pos = self.buf_start_pos
    buf_len = len(buffer)
    backup_state = None
    trace = self.trace
    while 1:
      if trace: #TRACE#
        print "State %d, %d/%d:%s -->" % ( #TRACE#
          state['number'], input_state, cur_pos, repr(cur_char)),  #TRACE#
      # Begin inlined self.save_for_backup()
      #action = state.action #@slow
      action = state['action'] #@fast
      if action:
        backup_state = (
          action, cur_pos, cur_line, cur_line_start, cur_char, input_state, next_pos)
      # End inlined self.save_for_backup()
      c = cur_char
      #new_state = state.new_state(c) #@slow
      new_state = state.get(c, -1) #@fast
      if new_state == -1: #@fast
        new_state = c and state.get('else') #@fast
      if new_state:
        if trace: #TRACE#
          print "State %d" % new_state['number']  #TRACE#
        state = new_state
        # Begin inlined: self.next_char()
        if input_state == 1:
          cur_pos = next_pos
          # Begin inlined: c = self.read_char()
          buf_index = next_pos - buf_start_pos
          if buf_index < buf_len:
            c = buffer[buf_index]
            next_pos = next_pos + 1
          else:
            discard = self.start_pos - buf_start_pos
            data = self.stream.read(0x1000)
            buffer = self.buffer[discard:] + data
            self.buffer = buffer
            buf_start_pos = buf_start_pos + discard
            self.buf_start_pos = buf_start_pos
            buf_len = len(buffer)
            buf_index = buf_index - discard
            if data:
              c = buffer[buf_index]
              next_pos = next_pos + 1
            else:
              c = ''
          # End inlined: c = self.read_char()
          if c == '\n':
            cur_char = EOL
            input_state = 2
          elif not c:
            cur_char = EOL
            input_state = 4
          else:
            cur_char = c
        elif input_state == 2:
          cur_char = '\n'
          input_state = 3
        elif input_state == 3:
          cur_line = cur_line + 1
          cur_line_start = cur_pos = next_pos
          cur_char = BOL
          input_state = 1
        elif input_state == 4:
          cur_char = EOF
          input_state = 5
        else: # input_state = 5
          cur_char = ''
        # End inlined self.next_char()
      else: # not new_state
        if trace: #TRACE#
          print "blocked"  #TRACE#
        # Begin inlined: action = self.back_up()
        if backup_state:
          (action, cur_pos, cur_line, cur_line_start, 
            cur_char, input_state, next_pos) = backup_state
        else:
          action = None
        break # while 1
        # End inlined: action = self.back_up()
    self.cur_pos = cur_pos
    self.cur_line = cur_line
    self.cur_line_start = cur_line_start
    self.cur_char = cur_char
    self.input_state = input_state
    self.next_pos	 = next_pos
    if trace: #TRACE#
      if action: #TRACE#
        print "Doing", action #TRACE#
    return action
    
#	def transition(self):
#		self.save_for_backup()
#		c = self.cur_char
#		new_state = self.state.new_state(c)
#		if new_state:
#			if self.trace:
#				print "Scanner: read: State %d: %s --> State %d" % (
#					self.state.number, repr(c), new_state.number)
#			self.state = new_state
#			self.next_char()
#			return 1
#		else:
#			if self.trace:
#				print "Scanner: read: State %d: %s --> blocked" % (
#					self.state.number, repr(c))
#			return 0
  
#	def save_for_backup(self):
#		action = self.state.get_action()
#		if action:
#			if self.trace:
#				print "Scanner: read: Saving backup point at", self.cur_pos
#			self.backup_state = (
#				action, self.cur_pos, self.cur_line, self.cur_line_start, 
#				self.cur_char, self.input_state, self.next_pos)
  
#	def back_up(self):
#		backup_state = self.backup_state
#		if backup_state:
#			(action, self.cur_pos, self.cur_line, self.cur_line_start, 
#				self.cur_char, self.input_state, self.next_pos) = backup_state
#			if self.trace:
#				print "Scanner: read: Backing up to", self.cur_pos
#			return action
#		else:
#			return None
  
  def next_char(self):
    input_state = self.input_state
    if self.trace:
      print "Scanner: next:", " "*20, "[%d] %d" % (input_state, self.cur_pos),
    if input_state == 1:
      self.cur_pos = self.next_pos
      c = self.read_char()
      if c == '\n':
        self.cur_char = EOL
        self.input_state = 2
      elif not c:
        self.cur_char = EOL
        self.input_state = 4
      else:
        self.cur_char = c
    elif input_state == 2:
      self.cur_char = '\n'
      self.input_state = 3
    elif input_state == 3:
      self.cur_line = self.cur_line + 1
      self.cur_line_start = self.cur_pos = self.next_pos
      self.cur_char = BOL
      self.input_state = 1
    elif input_state == 4:
      self.cur_char = EOF
      self.input_state = 5
    else: # input_state = 5
      self.cur_char = ''
    if self.trace:
      print "--> [%d] %d %s" % (input_state, self.cur_pos, repr(self.cur_char))
    
#	def read_char(self):
#		"""
#    Get the next input character, filling the buffer if necessary.
#    Returns '' at end of file.
#    """
#		next_pos = self.next_pos
#		buf_index = next_pos - self.buf_start_pos
#		if buf_index == len(self.buffer):
#			discard = self.start_pos - self.buf_start_pos
#			data = self.stream.read(0x1000)
#			self.buffer = self.buffer[discard:] + data
#			self.buf_start_pos = self.buf_start_pos + discard
#			buf_index = buf_index - discard
#			if not data:
#				return ''
#		c = self.buffer[buf_index]
#		self.next_pos = next_pos + 1
#		return c
  
  def position(self):
    """
    Return a tuple (name, line, col) representing the location of
    the last token read using the read() method. |name| is the
    name that was provided to the Scanner constructor; |line|
    is the line number in the stream (1-based); |col| is the
    position within the line of the first character of the token
    (0-based).
    """
    return (self.name, self.start_line, self.start_col)

  def begin(self, state_name):
    """Set the current state of the scanner to the named state."""
    self.initial_state = (
      self.lexicon.get_initial_state(state_name))
    self.state_name = state_name

  def produce(self, value, text = None):
    """
    Called from an action procedure, causes |value| to be returned
    as the token value from read(). If |text| is supplied, it is
    returned in place of the scanned text.

    produce() can be called more than once during a single call to an action
    procedure, in which case the tokens are queued up and returned one
    at a time by subsequent calls to read(), until the queue is empty,
    whereupon scanning resumes.
    """
    if text is None:
      text = self.text
    self.queue.append((value, text))

  def eof(self):
    """
    Override this method if you want something to be done at
    end of file.
    """

# For backward compatibility:
setattr(Scanner, "yield", Scanner.produce)
