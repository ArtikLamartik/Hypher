import subprocess
import sys
import os
import re

def p(line:str, prefix:str):
    if line.startswith(prefix):
        return True
    return False

def c(line:str, prefix:str):
    return line.removeprefix(prefix)

def s(line:str, pattern:str):
    return re.search(pattern, line)

def cf(filepath:str):
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(filepath, "w") as file:
        file.truncate()

def ri(line:str):
    return line.lstrip()

def gi(line:str):
    return line[:len(line) - len(line.lstrip())]

def rvs(varsize:int):
    values = {8:  "db", 16: "dw", 32: "dd", 64: "dq", 80: "dt"}
    return values[varsize]

def rrs(reservesize:int):
    values = {8:  "resb", 16: "resw", 32: "resd", 64: "resq", 80: "rest"}
    return values[reservesize]

def main(content:str, outputdir:str):
    index:int = 0
    currentfile:str = ""
    currentbits:str = ""
    currentorg:str = ""
    compileline:str = ""
    bdiskline:str = ""
    while index < len(content):
        line = content[index]
        original_line = line
        stripped_line = line.strip()
        indent = gi(original_line)
        if p(stripped_line, "#"):
            stripped_line = c(stripped_line, "#")
            if p(stripped_line, "compile"):
                compileline = c(stripped_line, "compile[")
                index += 1
                continue
            elif p(stripped_line, "bdisk"):
                bdiskline = c(stripped_line, "bdisk[")
                index += 1
                continue
            elif p(stripped_line, "file"):
                stripped_line = c(stripped_line, "file[")
                match = s(stripped_line, r"(.*?)\]")
                if match:
                    filename:str = match.group(1)
                    currentfile = outputdir + "/" + filename
                    cf(currentfile)
            elif p(stripped_line, "bits"):
                stripped_line = c(stripped_line, "bits[")
                match = s(stripped_line, r"(.*?)\]")
                if match and currentfile:
                    bits:str = match.group(1)
                    currentbits = bits
                    with open(currentfile, "a") as file:
                        file.write(f"[BITS {bits}]\n")
            elif p(stripped_line, "org"):
                stripped_line = c(stripped_line, "org[")
                match = s(stripped_line, r"(.*?)\]")
                if match and currentfile:
                    org:str = match.group(1)
                    currentorg = org
                    with open(currentfile, "a") as file:
                        file.write(f"[ORG {org}]\n")
        elif p(stripped_line, "$") and currentfile:
            stripped_line = c(stripped_line, "$")
            if p(stripped_line, "bootableid;"):
                with open(currentfile, "a") as file:
                    file.write(f"{indent}times 510 - ($ - $$) db 0\n{indent}db 0x55, 0xAA\n")
            elif p(stripped_line, "boot16"):
                stripped_line = c(stripped_line, "boot16[")
                match = s(stripped_line, r"(.*?)\];")
                if match:
                    addr:str = match.group(1)
                    with open(currentfile, "a") as file:
                        file.write(f"{indent}cli\n{indent}mov ax, 0x00\n{indent}mov ds, ax\n{indent}mov es, ax\n{indent}mov ss, ax\n{indent}mov sp, {currentorg}\n{indent}mov ah, 0x02\n{indent}mov al, 8\n{indent}mov ch, 0\n{indent}mov cl, 2\n{indent}mov dh, 0\n{indent}mov dl, 0x80\n{indent}mov bx, {addr}\n{indent}int 0x13\n{indent}jmp {addr}\n{indent}cli\n{indent}hlt\n")
            elif p(stripped_line, "kinit;"):
                with open(currentfile, "a") as file:
                    file.write(f"{indent}mov ax, 0x00\n{indent}mov ds, ax\n{indent}mov es, ax\n")
            elif p(stripped_line, "exit;"):
                with open(currentfile, "a") as file:
                    file.write(f"{indent}cli\n{indent}hlt\n")
        elif p(stripped_line, "%") and currentfile:
            stripped_line = c(stripped_line, "%")
            if p(stripped_line, "use"):
                stripped_line = c(stripped_line, "use[")
                match = s(stripped_line, r"(.*?)\];")
                if match:
                    filename:str = match.group(1)
                    with open(currentfile, "a") as file:
                        file.write(f"{indent}%include \"{filename}\"\n")
            elif p(stripped_line, "def"):
                stripped_line = c(stripped_line, "def ")
                match = s(stripped_line, r"(.*?)\s*\[(.*?)\]\s*->\s*{\s*(.*?)};")
                if match:
                    macroname:str = match.group(1)
                    macroargsize:int = int(eval(match.group(2)))
                    macrocode:list = match.group(3).split("\\n")
                    with open(currentfile, "a") as file:
                        file.write(f"%macro {macroname} {macroargsize}\n")
                        for macrolines in macrocode:
                            file.write(f"    {macrolines}\n")
                        file.write("%endmacro\n")
            elif p(stripped_line, "macro") or p(stripped_line, "endmacro"):
                with open(currentfile, "a") as file:
                    file.write(f"{line}")
        elif p(stripped_line, "@") and currentfile:
            stripped_line = c(stripped_line, "@")
            match = s(stripped_line, r"(.*?)\(\);")
            match2 = s(stripped_line, r"(.*?)\((.*?)\);")
            if match:
                funcname:str = match.group(1)
                with open(currentfile, "a") as file:
                    file.write(f"{indent}call {funcname}\n")
            elif match2:
                macroname:str = match2.group(1)
                args:str = match2.group(2)
                with open(currentfile, "a") as file:
                    file.write(f"{indent}{macroname} {args}\n")
        elif p(stripped_line, "fn") and currentfile:
            stripped_line = c(stripped_line, "fn ")
            match = s(stripped_line, r"(.*?)\(\):")
            if match:
                funcname:str = match.group(1)
                with open(currentfile, "a") as file:
                    file.write(f"{funcname}:\n")
        elif p(stripped_line, "let") and currentfile:
            stripped_line = c(stripped_line, "let ")
            match = s(stripped_line, r"(.*?):(.*?) = ([^\[\]]*?);(?:\s*(?![\"']|$))*$")
            match2 = s(stripped_line, r"(.*?):(.*?) = (.*?)\[\];(?:\s*(?![\"']|$))*$")
            match3 = s(stripped_line, r"(.*?):(.*?) = (.*?)\[(.*?)\];(?:\s*(?![\"']|$))*$")
            if match:
                varname:str = match.group(1)
                varsize:int = int(match.group(2))
                varcontent:str = match.group(3)
                vartype = rvs(varsize)
                with open(currentfile, "a") as file:
                    file.write(f"{varname} {vartype} {varcontent}\n")
            elif match2:
                reservename:str = match2.group(1)
                reservesize:int = int(match2.group(2))
                reservecount:str = match2.group(3)
                reservetype = rrs(reservesize)
                with open(currentfile, "a") as file:
                    file.write(f"{reservename} {reservetype} {reservecount}\n")
            elif match3:
                reservename:str = match3.group(1)
                reservesize:int = int(match3.group(2))
                reservecount:str = match3.group(3)
                reservevalue:str = match3.group(4)
                vartype = rvs(reservesize)
                with open(currentfile, "a") as file:
                    file.write(f"{reservename} {vartype} {reservecount} dup({reservevalue})\n")
        elif stripped_line and currentfile:
            with open(currentfile, "a") as file:
                file.write(f"{original_line}")
        else:
            if line != "" and currentfile:
                with open(currentfile, "a") as file:
                    file.write(f"{line}")
        index += 1
    compilematch = s(compileline, r"(.*?)\]\[(.*?)\]")
    if compilematch:
        asmfiles:list = compilematch.group(1).split(", ")
        buildfolder:str = compilematch.group(2)
        subprocess.run(["mkdir", "-p", buildfolder], check=True)
        for asmfile in asmfiles:
            binfilename = os.path.basename(asmfile).replace(".asm", ".bin")
            binfilepath = buildfolder + "/" + binfilename
            subprocess.run(["nasm", "-f", "bin", asmfile, "-o", binfilepath], check=True)
    bdiskmatch = s(bdiskline, r"(.*?)\]\[(.*?)\]\[(.*?)\]")
    if bdiskmatch:
        diskfile:str = bdiskmatch.group(1)
        disksize:int = int(eval(bdiskmatch.group(2)))
        binfiles:list = bdiskmatch.group(3).split(", ")
        with open(diskfile, "wb") as disk:
            for binfile in binfiles:
                with open(binfile, "rb") as binfl:
                    disk.write(binfl.read())
            disk.write(b"\x00" * (disksize - disk.tell()))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python main.py <filename> <output dir>")
        sys.exit(1)

    filename:str = sys.argv[1]
    outputdir:str = sys.argv[2]

    with open(filename, "r") as file:
        content:str = file.readlines()
        main(content, outputdir)
