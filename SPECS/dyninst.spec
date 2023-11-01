# For RHEL8 we need this before using any scl macro.
%global __python /usr/bin/python3

%{?scl:%scl_package dyninst}

Summary: An API for Run-time Code Generation
License: LGPLv2+
Name: %{?scl_prefix}dyninst
Group: Development/Libraries
Release: 2%{?dist}
URL: http://www.dyninst.org
Version: 10.2.1
Exclusiveos: linux
ExclusiveArch: %{ix86} x86_64 ppc64le aarch64

%define __testsuite_version 10.1.0
Source0: https://github.com/dyninst/dyninst/archive/v%{version}/dyninst-%{version}.tar.gz
Source1: https://github.com/dyninst/testsuite/archive/v%{__testsuite_version}/testsuite-%{__testsuite_version}.tar.gz

Patch1: dyninst-gcc11.patch
Patch2: dyninst-10.2.1-dbid.patch
Patch3: testsuite-10.1.0-gettid.patch
Patch4: testsuite-10.1.0-386.patch
Patch5: testsuite-10.1.0-throw.patch
Patch6: dyninst-10.2.1-tbb.patch

%global dyninst_base dyninst-%{version}
%global testsuite_base testsuite-%{__testsuite_version}


BuildRequires: zlib-devel
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: elfutils-devel
BuildRequires: elfutils-libelf-devel
BuildRequires: elfutils-debuginfod-client-devel
BuildRequires: boost-devel
BuildRequires: binutils-devel
BuildRequires: cmake
BuildRequires: libtirpc-devel
BuildRequires: tbb tbb-devel

%{?scl:Requires: %scl_runtime}

# Extra requires just for the testsuite
# NB, there's no separate libstdc++-static for <=el6
%if 0%{?rhel} >= 7
BuildRequires: libstdc++-static
%endif
BuildRequires: gcc-gfortran glibc-static libxml2-devel
%if 0%{?rhel} == 6
# C++11 requires devtoolset gcc.
BuildRequires: %{?scl_prefix}gcc-c++
%endif

# Testsuite files should not provide/require anything
%{?filter_setup:
%filter_provides_in %{_libdir}/dyninst/testsuite/
%filter_requires_in %{_libdir}/dyninst/testsuite/
%filter_setup
}

%description

Dyninst is an Application Program Interface (API) to permit the insertion of
code into a running program. The API also permits changing or removing
subroutine calls from the application program. Run-time code changes are
useful to support a variety of applications including debugging, performance
monitoring, and to support composing applications out of existing packages.
The goal of this API is to provide a machine independent interface to permit
the creation of tools and applications that use run-time code patching.

%package doc
Summary: Documentation for using the Dyninst API
Group: Documentation
%description doc
dyninst-doc contains API documentation for the Dyninst libraries.

%package devel
Summary: Header files for compiling programs with Dyninst
Group: Development/System
Requires: %{?scl_prefix}dyninst = %{version}-%{release}
Requires: boost-devel
Requires: tbb-devel

%description devel
dyninst-devel includes the C header files that specify the Dyninst user-space
libraries and interfaces. This is required for rebuilding any program
that uses Dyninst.

%package static
Summary: Static libraries for the compiling programs with Dyninst
Group: Development/System
Requires: %{?scl_prefix}dyninst-devel = %{version}-%{release}
%description static
dyninst-static includes the static versions of the library files for
the dyninst user-space libraries and interfaces.

%package testsuite
Summary: Programs for testing Dyninst
Group: Development/System
Requires: %{?scl_prefix}dyninst = %{version}-%{release}
Requires: %{?scl_prefix}dyninst-devel = %{version}-%{release}
Requires: %{?scl_prefix}dyninst-static = %{version}-%{release}
Requires: glibc-static
%description testsuite
dyninst-testsuite includes the test harness and target programs for
making sure that dyninst works properly.

%prep
%setup -q -n %{name}-%{version} -c
%setup -q -T -D -a 1

%patch1 -p1 -b .gcc11
%patch2 -p1 -b .dbid
%patch3 -p1 -b .gettid
%patch4 -p1 -b .386
%patch5 -p1 -b .throw
%patch6 -p1 -b .tbb

# cotire seems to cause non-deterministic gcc errors
# https://bugzilla.redhat.com/show_bug.cgi?id=1420551
sed -i.cotire -e 's/USE_COTIRE true/USE_COTIRE false/' \
  %{dyninst_base}/cmake/shared.cmake

%build

cd %{dyninst_base}

%if 0%{?rhel} == 6
# C++11 requires devtoolset gcc.
%{?scl:PATH=%{_bindir}${PATH:+:${PATH}}}
%endif

CFLAGS="$CFLAGS $RPM_OPT_FLAGS"
LDFLAGS="$LDFLAGS $RPM_LD_FLAGS"
%ifarch %{ix86}
    CFLAGS="$CFLAGS -fno-lto -march=i686"
    LDFLAGS="$LDFLAGS -fno-lto"
%endif    
CXXFLAGS="$CFLAGS"
export CFLAGS CXXFLAGS LDFLAGS

%cmake \
 -DENABLE_STATIC_LIBS=1 \
 -DENABLE_DEBUGINFOD=1 \
 -DCMAKE_BUILD_TYPE:STRING=None \
 -DINSTALL_LIB_DIR:PATH=%{_libdir}/dyninst \
 -DINSTALL_INCLUDE_DIR:PATH=%{_includedir}/dyninst \
 -DINSTALL_CMAKE_DIR:PATH=%{_libdir}/cmake/Dyninst \
 -DBoost_NO_BOOST_CMAKE=ON \
 -DCMAKE_SKIP_RPATH:BOOL=YES \
 .
%make_build

# Hack to install dyninst nearby, so the testsuite can use it
make DESTDIR=../install install
find ../install -name '*.cmake' -execdir \
  sed -i -e 's!%{_prefix}!../install&!' '{}' '+'
# cmake mistakenly looks for libtbb.so in the dyninst install dir
sed -i '/libtbb.so/ s/".*usr/"\/usr/' $PWD/../install%{_libdir}/cmake/Dyninst/commonTargets.cmake

cd ../%{testsuite_base}
%cmake \
 -DDyninst_DIR:PATH=$PWD/../install%{_libdir}/cmake/Dyninst \
 -DINSTALL_DIR:PATH=%{_libdir}/dyninst/testsuite \
 -DCMAKE_BUILD_TYPE:STRING=Debug \
 -DBoost_NO_BOOST_CMAKE=ON \
 -DCMAKE_SKIP_RPATH:BOOL=YES \
 .
%make_build

%install

cd %{dyninst_base}
%make_install

# It doesn't install docs the way we want, so remove them.
# We'll just grab the pdfs later, directly from the build dir.
rm -v %{buildroot}%{_docdir}/*-%{version}.pdf

cd ../%{testsuite_base}
%make_install

# Ugly hack to mask testsuite files from debuginfo extraction.  Running the
# testsuite requires debuginfo, so extraction is useless.  However, debuginfo
# extraction is still nice for the main libraries, so we don't want to disable
# it package-wide.  The permissions are restored by attr(755,-,-) in files.
find %{buildroot}%{_libdir}/dyninst/testsuite/ \
  -type f '!' -name '*.a' -execdir chmod 644 '{}' '+'

%files
%defattr(-,root,root,-)

%dir %{_libdir}/dyninst
%{_libdir}/dyninst/*.so.*
# dyninst mutators dlopen the runtime library
%{_libdir}/dyninst/libdyninstAPI_RT.so

%doc %{dyninst_base}/COPYRIGHT
%doc %{dyninst_base}/LICENSE.md

%files doc
%defattr(-,root,root,-)
%doc %{dyninst_base}/dataflowAPI/doc/dataflowAPI.pdf
%doc %{dyninst_base}/dynC_API/doc/dynC_API.pdf
%doc %{dyninst_base}/dyninstAPI/doc/dyninstAPI.pdf
%doc %{dyninst_base}/instructionAPI/doc/instructionAPI.pdf
%doc %{dyninst_base}/parseAPI/doc/parseAPI.pdf
%doc %{dyninst_base}/patchAPI/doc/patchAPI.pdf
%doc %{dyninst_base}/proccontrol/doc/proccontrol.pdf
%doc %{dyninst_base}/stackwalk/doc/stackwalk.pdf
%doc %{dyninst_base}/symtabAPI/doc/symtabAPI.pdf

%files devel
%defattr(-,root,root,-)
%{_includedir}/dyninst
%{_libdir}/dyninst/*.so
%{_libdir}/cmake/Dyninst

%files static
%defattr(-,root,root,-)
%{_libdir}/dyninst/*.a

%files testsuite
%defattr(-,root,root,-)
%{_bindir}/parseThat
%dir %{_libdir}/dyninst/testsuite/
%attr(755,root,root) %{_libdir}/dyninst/testsuite/*[!a]
%attr(644,root,root) %{_libdir}/dyninst/testsuite/*.a

%changelog
* Fri Nov 06 2020 Stan Cox <scox@redhat.com> - 10.2.1-2
- Enable debuginfod

* Wed Oct 28 2020 Stan Cox <scox@redhat.com> - 10.2.1-1
- Update to 10.2.1

* Mon Jun 1 2020 Martin Cermak <mcermak@redhat.com> - 10.1.0-2
- NVR Bump and rebuild

* Sun Jun 9 2019 Stan Cox <scox@redhat.com> - 10.1.0-1
- Update to 10.1.0
