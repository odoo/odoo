# #!/usr/bin/perl
snippet #!
	#!/usr/bin/env perl

# Hash Pointer
snippet .
	 =>
# Function
snippet sub
	sub ${1:function_name} {
		${2:#body ...}
	}
# Conditional
snippet if
	if (${1}) {
		${2:# body...}
	}
# Conditional if..else
snippet ife
	if (${1}) {
		${2:# body...}
	}
	else {
		${3:# else...}
	}
# Conditional if..elsif..else
snippet ifee
	if (${1}) {
		${2:# body...}
	}
	elsif (${3}) {
		${4:# elsif...}
	}
	else {
		${5:# else...}
	}
# Conditional One-line
snippet xif
	${1:expression} if ${2:condition};${3}
# Unless conditional
snippet unless
	unless (${1}) {
		${2:# body...}
	}
# Unless conditional One-line
snippet xunless
	${1:expression} unless ${2:condition};${3}
# Try/Except
snippet eval
	local $@;
	eval {
		${1:# do something risky...}
	};
	if (my $e = $@) {
		${2:# handle failure...}
	}
# While Loop
snippet wh
	while (${1}) {
		${2:# body...}
	}
# While Loop One-line
snippet xwh
	${1:expression} while ${2:condition};${3}
# C-style For Loop
snippet cfor
	for (my $${2:var} = 0; $$2 < ${1:count}; $$2${3:++}) {
		${4:# body...}
	}
# For loop one-line
snippet xfor
	${1:expression} for @${2:array};${3}
# Foreach Loop
snippet for
	foreach my $${1:x} (@${2:array}) {
		${3:# body...}
	}
# Foreach Loop One-line
snippet fore
	${1:expression} foreach @${2:array};${3}
# Package
snippet package
	package ${1:`substitute(Filename('', 'Page Title'), '^.', '\u&', '')`};

	${2}

	1;

	__END__
# Package syntax perl >= 5.14
snippet packagev514
	package ${1:`substitute(Filename('', 'Page Title'), '^.', '\u&', '')`} ${2:0.99};

	${3}

	1;

	__END__
#moose
snippet moose
	use Moose;
	use namespace::autoclean;
	${1:#}BEGIN {extends '${2:ParentClass}'};

	${3}
# parent
snippet parent
	use parent qw(${1:Parent Class});
# Read File
snippet slurp
	my $${1:var} = do { local $/; open my $file, '<', "${2:file}"; <$file> };
	${3}
# strict warnings
snippet strwar
	use strict;
	use warnings;
# older versioning with perlcritic bypass
snippet vers
	## no critic
	our $VERSION = '${1:version}';
	eval $VERSION;
	## use critic
# new 'switch' like feature
snippet switch
	use feature 'switch';

# Anonymous subroutine
snippet asub
	sub {
	 	${1:# body }
	}



# Begin block
snippet begin
	BEGIN {
		${1:# begin body}
	}

# call package function with some parameter
snippet pkgmv
	__PACKAGE__->${1:package_method}(${2:var})

# call package function without a parameter
snippet pkgm
	__PACKAGE__->${1:package_method}()

# call package "get_" function without a parameter
snippet pkget
	__PACKAGE__->get_${1:package_method}()

# call package function with a parameter
snippet pkgetv
	__PACKAGE__->get_${1:package_method}(${2:var})

# complex regex
snippet qrx
	qr/
	     ${1:regex}
	/xms

#simpler regex
snippet qr/
	qr/${1:regex}/x

#given
snippet given
	given ($${1:var}) {
		${2:# cases}
		${3:# default}
	}

# switch-like case
snippet when
	when (${1:case}) {
		${2:# body}
	}

# hash slice
snippet hslice
	@{ ${1:hash}  }{ ${2:array} }


# map
snippet map
	map {  ${2: body }    }  ${1: @array } ;



# Pod stub
snippet ppod
	=head1 NAME

	${1:ClassName} - ${2:ShortDesc}

	=head1 SYNOPSIS

	  use $1;

	  ${3:# synopsis...}

	=head1 DESCRIPTION

	${4:# longer description...}


	=head1 INTERFACE


	=head1 DEPENDENCIES


	=head1 SEE ALSO


# Heading for a subroutine stub
snippet psub
	=head2 ${1:MethodName}

	${2:Summary....}

# Heading for inline subroutine pod
snippet psubi
	=head2 ${1:MethodName}

	${2:Summary...}


	=cut
# inline documented subroutine
snippet subpod
	=head2 $1

	Summary of $1

	=cut

	sub ${1:subroutine_name} {
		${2:# body...}
	}
# Subroutine signature
snippet parg
	=over 2

	=item
	Arguments


	=over 3

	=item
	C<${1:DataStructure}>

	  ${2:Sample}


	=back


	=item
	Return

	=over 3


	=item
	C<${3:...return data}>


	=back


	=back



# Moose has
snippet has
	has ${1:attribute} => (
		is	    => '${2:ro|rw}',
		isa 	=> '${3:Str|Int|HashRef|ArrayRef|etc}',
		default => sub {
			${4:defaultvalue}
		},
		${5:# other attributes}
	);


# override
snippet override
	override ${1:attribute} => sub {
		${2:# my $self = shift;};
		${3:# my ($self, $args) = @_;};
	};


# use test classes
snippet tuse
	use Test::More;
	use Test::Deep; # (); # uncomment to stop prototype errors
	use Test::Exception;

# local test lib
snippet tlib
	use lib qw{ ./t/lib };

#test methods
snippet tmeths
	$ENV{TEST_METHOD} = '${1:regex}';

# runtestclass
snippet trunner
	use ${1:test_class};
	$1->runtests();

# Test::Class-style test
snippet tsub
	sub t${1:number}_${2:test_case} :Test(${3:num_of_tests}) {
		my $self = shift;
		${4:#  body}

	}

# Test::Routine-style test
snippet trsub
	test ${1:test_name} => { description => '${2:Description of test.}'} => sub {
		my ($self) = @_;
		${3:# test code}
	};

#prep test method
snippet tprep
	sub prep${1:number}_${2:test_case} :Test(startup) {
		my $self = shift;
		${4:#  body}
	}

# cause failures to print stack trace
snippet debug_trace
	use Carp; # 'verbose';
	# cloak "die"
	# warn "warning"
	$SIG{'__DIE__'} = sub {
		require Carp; Carp::confess
	};

