{
  description = "Sigrok tools (pulseview, dsview) with custom protocol decoders";

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

        # Override libsigrokdecode to include custom decoders
        libsigrokdecode-custom = pkgs.libsigrokdecode.overrideAttrs (oldAttrs: {
          postInstall = (oldAttrs.postInstall or "") + ''
            cp -r ${customDecoders}/* $out/share/libsigrokdecode/decoders/
          '';
        });

        # Pulseview with custom libsigrokdecode
        pulseview-custom = pkgs.pulseview.override {
          libsigrokdecode = libsigrokdecode-custom;
        };

        # DSView with custom decoders patched into the source
        dsview-custom = pkgs.dsview.overrideAttrs (oldAttrs: {
          postPatch = (oldAttrs.postPatch or "") + ''
            cp -r ${customDecoders}/* libsigrokdecode4DSL/decoders/
          '';
        });
      in
      {
        packages = {
          pulseview = pulseview-custom;
          dsview = dsview-custom;
          default = dsview-custom;
        };
      }
    );
}
