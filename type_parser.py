import json

import cmake_parser.ast

from cpp_parser import *


def get_content_as_str(file_path):
    with open(file_path, 'r') as f:
        return f.read()


def parse_c_make_lists(file_path):
    content = get_content_as_str(file_path)
    # res = cmake_parser.parse_tree(content)
    cmake_ast = cmake_parser.parse_raw(content)
    res = []
    for ast_node in cmake_ast:
        if isinstance(ast_node, cmake_parser.ast.Comment):
            res.append(ast_node)
        print(ast_node)
        print("  ", type(ast_node), isinstance(ast_node, cmake_parser.ast.Comment))


def run():
    parse_c_make_lists('../test/CMakeLists.txt')


def find_sizeof_usage(stmt):
    pass


# 识别出声明（包括参数声明、函数体中的声明）中的类型信息（包括基础类型、自定义类型等），以及所有的标识符信息（包括变量、常量等）
def parse_declaration(decl_stmt):
    res = {}
    type_info = None
    for decl_item in decl_stmt.children:
        # 识别声明的类型信息，如果识别不了则无法返回结果
        if (decl_item.type == 'type_identifier'
                or decl_item.type == 'primitive_type'):
            type_info = (decl_item.text.decode(), decl_item.type)
            continue
        if not type_info:
            continue

        def dfs_find_declared_identifier(node):
            if node.type == 'identifier':
                return node.text.decode()
            for node_item in node.children:
                sub_identifier = dfs_find_declared_identifier(node_item)
                if sub_identifier:
                    return sub_identifier
            return None

        identifier = dfs_find_declared_identifier(decl_item)
        if identifier:
            res[identifier] = type_info
    return res


def parse_sizeof_uses(sizeof_expression):
    # 从sizeof中提取操作符变量
    def dfs_parse_operand(ele):
        uses = set()
        if ele.type == 'identifier':
            uses.add(ele.text.decode())
        else:
            for child in ele.children:
                sub_uses = dfs_parse_operand(child)
                uses.update(sub_uses)
        return uses

    res = dfs_parse_operand(sizeof_expression.children[1])
    return res


def dfs_decl_and_use(node):
    decls = dict()  # 当前语句（可能是个作用域）中产生的定义
    uses = set()
    undefined_types = set()

    # 识别到sizeof操作，提取sizeof中使用的变量、类型等信息
    if node.type == 'sizeof_expression':
        current_uses = parse_sizeof_uses(node)
        uses.update(current_uses)
        # print('[current_uses]', ele.text.decode(), '--->', current_uses)

    # 识别变量声明，并添加到当前的作用域下，用于确认被使用的变量是否经过声明
    if node.type == 'declaration':
        # 提取声明语句中的标识符信息
        current_decls = parse_declaration(node)
        decls.update(current_decls)
    elif node.type == 'parameter_declaration':
        # todo 从参数中读取
        param_decls = parse_declaration(node)
        decls.update(param_decls)

    # print(node.text.decode(), node.type)
    # 查找子节点下产生的定义，以及sizeof操作数等信息
    for child in node.children:
        # 获取子节点中的声明以及使用的数据信息
        sub_node_decls, sub_node_uses, sub_node_undefined_types = dfs_decl_and_use(child)

        # 提取子节点中非基础类型的类型信息
        mapped_decls_uses = sub_node_uses.intersection(decls)
        if mapped_decls_uses:
            new_undefined_types = {decls[key][0] for key in mapped_decls_uses if decls[key][1] == 'type_identifier'}
            undefined_types.update(new_undefined_types)
            # print('Undefined types:', new_undefined_types)

        # 更新所有的数据声明与使用情况
        sub_node_uses.difference_update(decls)
        decls.update(sub_node_decls)
        uses.update(sub_node_uses)
        undefined_types.update(sub_node_undefined_types)

    # 部分节点类型定义了数据的作用域边界，声明的数据不应当传播到该作用域外部
    if (node.type == 'compound_statement' or
            node.type == 'for_statement' or
            node.type == 'function_definition'):
        decls.clear()

    # 返回结果为当前Node所在作用域下的声明，以及尚未发现声明的sizeof操作数
    return decls, uses, undefined_types



typedef_recorder = dict()  # 类型名称 => 路径 => 定义文本 （防止不同文件中出现同名的类型定义）


def parse_typedef(node, file_path):
    for child_item in node.children:
        if child_item.type == 'type_identifier':
            # 记录类型信息
            print("类型标识符", child_item.text.decode())
            type_identifier = child_item.text.decode()
            if type_identifier not in typedef_recorder:
                typedef_recorder[type_identifier] = []
            typedefs = typedef_recorder[type_identifier]
            typedefs.append((file_path, node.text.decode()))


def build_file_dependency_graph():
    # 有没有可能，A依赖于B，B依赖于C，A使用了C中定义的类型？
    pass


def get_typedef(type_identifier):
    # 从typedefs中获取想要的类型信息
    # 如果存在多个同名的定义，可能还需要判断实际依赖是哪个
    # 暂时只考虑最简单的情况，即假设一个项目中不存在相同的定义
    if type_identifier not in typedef_recorder:
        print("未找到类型定义", type_identifier)
        return None

    typedefs = typedef_recorder[type_identifier]
    if len(typedefs) > 1:
        print("类型{}存在多个定义：".format(type_identifier), "可能需要解析文件依赖关系")
        for item in typedefs:
            print(item)
        return None
    return typedefs[0]


def raw_parse(file_path):
    code = get_content_as_str(file_path)
    ast_root = parse_src_str(code)  # 整个文件

    for item in ast_root.children:
        if item.type == 'type_definition':
            type_def_node = item
            parse_typedef(type_def_node, file_path)

        elif item.type == 'function_definition':
            func_def_node = item
            decls, uses, undefined_types = dfs_decl_and_use(func_def_node)
            if len(decls) != 0:
                print("非预期行为：数据声明应控制在函数内")
            print("未找到声明的数据：", uses)
            print("未定义的类型：", undefined_types)

    print(json.dumps(typedef_recorder, indent=4))
    '''
    todo
    1.尝试从文件中查找数据声明，以及未定义的类型，对应sizeof误用第二个例子
    2.尝试跨文件查找类型定义，对应之前的误报
    3.在当前代码仓以及新的代码仓中验证当前实现的效果
    '''

    # if
    # function_body = get_function_body(func_def_node)
    # print(function_body.text.decode())
    # stmts = get_function_stmts(function_body)
    # for stmt in stmts:
    #     dfs(stmt)

    # for item in stmts:
    #     print(item)
    # pass



# 迭代到sizeof的地方，然后解析其中的数据标识符信息
# 遍历类型信息


if __name__ == '__main__':
    raw_parse("./func.txt")
