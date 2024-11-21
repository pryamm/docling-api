import torch

print(f"MPS (Apple Metal) available: {hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()}")
print(f"MPS backend built: {torch.backends.mps.is_built()}")