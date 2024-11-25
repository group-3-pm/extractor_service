def markdown_to_csv(md: str) -> str:
    lines = md.split("\n")
    csv = []
    for line in lines:
        if line.startswith("|"):
            csv.append(line)
    return "\n".join(csv)