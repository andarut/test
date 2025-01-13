#./.venv/bin/python3

import ast

class NestedFunctionEliminator(ast.NodeTransformer):
    def __init__(self):
        self.counter = 0
        self.assignments = []

    def visit_FunctionDef(self, node):
        self.counter = 0
        self.assignments = []
        self.generic_visit(node)
        node.body = self.assignments + node.body
        return node

    def create_assign(self, target, value):
        assign = ast.Assign(targets=[ast.Name(id=target, ctx=ast.Store())], value=value)
        ast.copy_location(assign, value)
        return assign

    def process_expr(self, node):
        if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Call)):
            var_name = f'v{self.counter}'
            self.counter += 1
            self.assignments.append(self.create_assign(var_name, node))
            return ast.Name(id=var_name, ctx=ast.Load())
        return node

    def visit_BinOp(self, node):
        node.left = self.process_expr(self.visit(node.left))
        node.right = self.process_expr(self.visit(node.right))
        return node

    def visit_UnaryOp(self, node):
        node.operand = self.process_expr(self.visit(node.operand))
        return node

    def visit_Call(self, node):
        node.func = self.visit(node.func)
        node.args = [self.process_expr(self.visit(arg)) for arg in node.args]
        # Оставляем ast.keyword без изменений
        node.keywords = [ast.keyword(arg=kw.arg, value=self.visit(kw.value)) for kw in node.keywords]
        return node

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
            # Оставляем присваивания вида (ast.Name = ast.Name) без изменений
            return node
        node.value = self.process_expr(self.visit(node.value))
        return node

    def visit_Return(self, node):
        if isinstance(node.value, ast.Tuple):
            node.value.elts = [self.process_expr(self.visit(elt)) for elt in node.value.elts]
        else:
            node.value = self.process_expr(self.visit(node.value))
        return node

def transform_code(code):
    tree = ast.parse(code)
    transformer = NestedFunctionEliminator()
    new_tree = transformer.visit(tree)
    return ast.unparse(new_tree)

# Тестовый код
test_code = """
def foo(a, b, c, d):
    return baz(-a, c**(a - b) + d, k=A + 123)

def bar(x):
    a = x * 2 + sin(x)
    b = a
    return a, b, x + 1
"""

transformed_code = transform_code(test_code)
print(transformed_code)

'''
def foo(a, b, c, d):
    v0 = -a
    v1 = a - b
    v2 = c ** v1
    v3 = v2 + d
    v4 = baz(v0, v3, k=A + 123)
    return v4

def bar(x):
    v0 = x * 2
    v1 = sin(x)
    v2 = v0 + v1
    v3 = x + 1
    a = v2
    b = a
    return (a, b, v3)
'''
