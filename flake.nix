{
  description = "DSView with custom protocol decoders";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        # Custom decoders from this repository
        customDecoders = ./decoders;

        # DSView with custom decoders patched into the source
        dsview-custom = pkgs.dsview.overrideAttrs (oldAttrs: {
          postPatch = (oldAttrs.postPatch or "") + ''
            cp -r ${customDecoders}/* libsigrokdecode4DSL/decoders/
          '';
        });
      in
      {
        packages = {
          dsview = dsview-custom;
          default = dsview-custom;
        };
      }
    );
}
