import os

def print_tree(start, prefix=""):
    files = sorted(os.listdir(start))
    for i, file in enumerate(files):
        path = os.path.join(start, file)
        connector = "├── " if i < len(files) - 1 else "└── "
        print(prefix + connector + file)
        if os.path.isdir(path):
            extension = "│   " if i < len(files) - 1 else "    "
            print_tree(path, prefix + extension)

print_tree(".")
