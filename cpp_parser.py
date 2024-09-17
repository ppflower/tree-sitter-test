import sys

import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Node

LANGUAGE = Language(tscpp.language())
parser = Parser(LANGUAGE)


def parse():
    with open("../test/test.cpp", "r") as f:
        src_str = f.read()
        src_bytes = bytes(src_str, encoding='utf-8')

    tree = parser.parse(src_bytes)
    return tree.root_node


def parse_src_str(src_str):
    src_bytes = bytes(src_str, encoding='utf-8')
    tree = parser.parse(src_bytes)
    return tree.root_node


# 获取类型以及函数定义
def get_type_function_definitions(root_node):
    type_definitions = []
    function_definitions = []
    for child in root_node.children:
        if child.type == 'type_definition':
            type_definitions.append(child)
        elif child.type == 'function_definition':
            function_definitions.append(child)
    return type_definitions, function_definitions


def get_type_definitions(root_node):
    res = []
    for child in root_node.children:
        if child.type == 'type_definition':
            res.append(child)
    return res


def get_function_definitions(root_node):
    res = []
    for child in root_node.children:
        if child.type == 'function_definition':
            res.append(child)
    return res


def get_function_name(function_definition_node):
    def dfs(ast_node, stack):
        stack.append(ast_node)
        if ast_node.type == 'function_declarator':
            return
        for child in ast_node.children:
            dfs(child, stack)
            if stack[-1] != ast_node:
                return
        if stack[-1] == ast_node:
            stack.pop()

    path = []
    dfs(function_definition_node, path)
    return path[-1].text.decode()


def get_function_params(function_definition_node):
    for func_def_ele in function_definition_node.children:
        if func_def_ele.type == 'function_declarator':
            for func_decl_ele in func_def_ele.children:
                # identifier/parameter_list
                if func_decl_ele.type == 'parameter_list':
                    return parse_params(func_decl_ele)
    return None


# parameter_list实际上不仅包含了参数，还包含了左右括号，以及分隔参数的逗号，需做一次过滤
def parse_params(parameter_list):
    res = []
    for param_ele in parameter_list.children:
        if param_ele.type == 'parameter_declaration':
            res.append(param_ele)
    return res


def parse_param(param_decl):
    param_decl_elements = param_decl.children
    return param_decl_elements[0], param_decl_elements[1]


# 返回函数体，暂时用不到
def get_function_body(function_definition_node):
    for func_def_ele in function_definition_node.children:
        if func_def_ele.type == 'compound_statement':
            return func_def_ele
    return None


def get_function_stmts(function_body):
    if isinstance(function_body.children, list) and len(function_body.children) >= 2:
        # print(1)
        # print(function_body.children[0].text, function_body.children[1].text)
        if function_body.children[0].text.decode() == '{' and function_body.children[-1].text.decode() == '}':
            return function_body.children[1:-1]
    print("获取函数语句失败")
    return None


def test():
    root_node = parse()
    print(root_node.type)

    # 获取文件中顶层的函数节点
    functions = get_function_definitions(root_node)
    for function in functions:
        function_name = get_function_name(function)
        print("  ", function_name)
        function_params = get_function_params(function)
        for function_param in function_params:
            # print("    ", function_param.type, function_param)
            param_type, param_name = parse_param(function_param)
            print("    ", param_type, param_name)


if __name__ == "__main__":
    test()
