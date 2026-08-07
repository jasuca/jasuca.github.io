# jasuca.github.io

This repository mirrors the production build of [jasuca.com](https://jasuca.com), whose
source lives in [jasuca/jasuca-com](https://github.com/jasuca/jasuca-com).

The `Sync jasuca.com` workflow checks the source repository every hour, rebuilds it, and
commits the generated static files here when they change. It then explicitly requests a
GitHub Pages rebuild because commits made with the workflow token do not trigger one.

The workflow can also be run on demand from the Actions tab.
