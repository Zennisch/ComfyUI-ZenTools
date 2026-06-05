# ComfyUI-ZNS-Utils

A collection of utility nodes for ComfyUI, including flow control and image configuration tools.

> [!NOTE]
> This projected was created with a [cookiecutter](https://github.com/Comfy-Org/cookiecutter-comfy-extension) template. It helps you start writing custom nodes without worrying about the Python setup.

## Quickstart

1. Install [ComfyUI](https://docs.comfy.org/get_started).
1. Install [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)
1. Look up this extension in ComfyUI-Manager. If you are installing manually, clone this repository under `ComfyUI/custom_nodes`.
1. Restart ComfyUI.

## Features

### Switch Any - Flow Control Node

The **Switch Any** node enables conditional execution in ComfyUI workflows. It passes data through when enabled, or blocks the entire downstream pipeline when disabled.

#### Key Characteristics

- **Single Input**: Accepts any data type via `source` input
- **Boolean Switch**: Control execution with a boolean switch (ON/OFF)
- **Complete Block**: When OFF, removes not only itself but all connected downstream nodes from the execution DAG
- **Type Agnostic**: No type checking—supports ANY input type

#### How It Works

```
         ┌─────────────┐
source ──┤             │
         │ Switch Any  ├─── output (data passes through)
switch ──┤             │     (or blocked if OFF)
         └─────────────┘
         
When switch = ON:  data flows normally to downstream nodes
When switch = OFF: this node AND all downstream nodes are removed from DAG
```

#### Usage Example

**Scenario**: Conditionally apply a filter to an image

```
LoadImage ──┐
            ├─→ Switch Any ──→ Filter ──→ SaveImage
         OFF┘    (switch controlled by UI toggle)
```

- If switch is **ON**: Filter is applied (LoadImage → Filter → SaveImage)
- If switch is **OFF**: Entire FilterSaveImage branch is removed (only LoadImage executes)

#### Implementation Details

The Switch Any node uses a **validation hook pattern** to intercept ComfyUI's prompt validation process:

1. **Find Phase**: Before execution, locate all SwitchAny nodes in the workflow
2. **Resolve Phase**: Determine each switch's boolean state (from direct value or connected node)
3. **Block Phase**: Remove downstream nodes when switch is OFF
4. **Cascade Phase**: Recursively remove any nodes that depend on the removed nodes
5. **Execute Phase**: Run the modified workflow with ComfyUI's normal validation

**Error Handling**:
- If a switch's boolean value cannot be determined, the workflow validation fails with a clear error message
- Boolean must be determinable at queue time (direct UI toggle or connected primitive boolean node)

#### Limitations

- Runtime boolean determination is not supported (e.g., boolean output from a computation node won't be evaluated)
- For complex branching, chain multiple Switch Any nodes or use them in combination with other flow control nodes

---

### Basic Image Config

Configuration node for image dimensions and scaling.

- **Inputs**: Base width, base height, scale factor, batch size
- **Outputs**: Base dimensions, scaled dimensions, batch size
- **Use Case**: Centralized image configuration that can be referenced throughout the workflow

## Develop

To install the dev dependencies and pre-commit (will run the ruff hook), do:

```bash
cd comfyui_zns_utils
pip install -e .[dev]
pre-commit install
```

The `-e` flag above will result in a "live" install, in the sense that any changes you make to your node extension will automatically be picked up the next time you run ComfyUI.

## Publish to Github

Install Github Desktop or follow these [instructions](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) for ssh.

1. Create a Github repository that matches the directory name. 
2. Push the files to Git
```
git add .
git commit -m "project scaffolding"
git push
``` 

## Writing custom nodes

An example custom node is located in [node.py](src/comfyui_zns_utils/nodes.py). To learn more, read the [docs](https://docs.comfy.org/essentials/custom_node_overview).


## Tests

This repo contains unit tests written in Pytest in the `tests/` directory. It is recommended to unit test your custom node.

- [build-pipeline.yml](.github/workflows/build-pipeline.yml) will run pytest and linter on any open PRs
- [validate.yml](.github/workflows/validate.yml) will run [node-diff](https://github.com/Comfy-Org/node-diff) to check for breaking changes

## Publishing to Registry

If you wish to share this custom node with others in the community, you can publish it to the registry. We've already auto-populated some fields in `pyproject.toml` under `tool.comfy`, but please double-check that they are correct.

You need to make an account on https://registry.comfy.org and create an API key token.

- [ ] Go to the [registry](https://registry.comfy.org). Login and create a publisher id (everything after the `@` sign on your registry profile). 
- [ ] Add the publisher id into the pyproject.toml file.
- [ ] Create an api key on the Registry for publishing from Github. [Instructions](https://docs.comfy.org/registry/publishing#create-an-api-key-for-publishing).
- [ ] Add it to your Github Repository Secrets as `REGISTRY_ACCESS_TOKEN`.

A Github action will run on every git push. You can also run the Github action manually. Full instructions [here](https://docs.comfy.org/registry/publishing). Join our [discord](https://discord.com/invite/comfyorg) if you have any questions!

