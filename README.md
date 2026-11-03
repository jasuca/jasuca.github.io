# jasuca.github.io

This repository mirrors the production build of [jasuca.com](https://jasuca.com), whose
source lives in [jasuca/jasuca-com](https://github.com/jasuca/jasuca-com).

Pushes to `main` in the source repository automatically publish the CI-verified
build here after checks pass. The source repository holds the
`JASUCA_MIRROR_DEPLOY_KEY` Actions secret; its public key is registered here as the
write-enabled deploy key `jasuca.com automatic mirror publishing`. SSH pushes
trigger the normal GitHub Pages build. Superseded source pushes are skipped.
The `.source-commit` file identifies the source SHA used for the mirrored build;
reruns of the same source and build do not create commits.

For a manual rebuild, run the `Sync jasuca.com` workflow from the Actions tab to rebuild the source,
commit changed static files here, and explicitly request a GitHub Pages rebuild. Commits
made with the workflow token do not trigger a Pages build on their own.

## Private source access

The source checkout uses the `JASUCA_SOURCE_DEPLOY_KEY` Actions secret. Its matching
public key is registered as a **read-only** deploy key on `jasuca/jasuca-com`, named
`jasuca.github.io mirror source checkout`. The mirror checkout and publishing steps
continue to use this repository's workflow token.

To rotate the credential, generate a dedicated SSH key pair, add the public key to
the source repository's deploy keys with write access disabled, replace the mirror
Actions secret with the private key, and run `Sync jasuca.com` successfully before
removing the old source deploy key. Never commit the private key.
