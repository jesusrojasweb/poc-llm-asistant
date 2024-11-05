{pkgs}: {
  deps = [
    pkgs.unixtools.ping
    pkgs.iana-etc
    pkgs.postgresql
  ];
}
